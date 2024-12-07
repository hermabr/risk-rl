from risk.country import *
from risk.player import Player
import logging

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv

class RiskGNN(nn.Module):
    def __init__(self, in_channels_node, hidden_dim, num_actions):
        super(RiskGNN, self).__init__()
        self.conv1 = GCNConv(in_channels_node, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, hidden_dim)
        self.action_head = ActionHead(hidden_dim, num_actions)

    def forward(self, x, edge_index, action_lookup_table):
        # x: node features
        # edge_index: edge list array
        x = F.relu(self.conv1(x, edge_index))
        x = F.relu(self.conv2(x, edge_index)) # (num_nodes, hidden_dim)

        logits = self.action_head(x, action_lookup_table)  # [num_actions]
        return logits
    
class ActionHead(nn.Module):
    def __init__(self, node_embed_dim, num_actions):
        super(ActionHead, self).__init__()
        self.node_embed_dim = node_embed_dim
        self.num_actions = num_actions

        self.skip_attack_embed = nn.Parameter(torch.zeros(node_embed_dim))
        self.skip_defend_embed = nn.Parameter(torch.zeros(node_embed_dim))

        self.mlp = nn.Sequential(
            nn.Linear(2 * node_embed_dim + 1, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )

    def forward(self, node_embeddings, action_lookup_table):
        attack_indices = torch.tensor(
            [action[0] for action in action_lookup_table],
            dtype=torch.long,
            device=node_embeddings.device
        )  # [num_actions]
        
        defend_indices = torch.tensor(
            [action[1] for action in action_lookup_table],
            dtype=torch.long,
            device=node_embeddings.device
        )  # [num_actions]
        
        n_soldiers = torch.tensor(
            [action[2] for action in action_lookup_table],
            dtype=torch.float32,
            device=node_embeddings.device
        ).unsqueeze(1)  # [num_actions, 1]
        
        skip_mask = (attack_indices == -1)  # [num_actions]
        attack_embeds = self.skip_attack_embed.unsqueeze(0).repeat(attack_indices.size(0), 1)  # [num_actions, node_embed_dim]
        defend_embeds = self.skip_defend_embed.unsqueeze(0).repeat(defend_indices.size(0), 1)  # [num_actions, node_embed_dim]
        
        non_skip_mask = ~skip_mask  # [num_actions]
        attack_embeds[non_skip_mask] = node_embeddings[attack_indices[non_skip_mask]]
        defend_embeds[non_skip_mask] = node_embeddings[defend_indices[non_skip_mask]]
        
        action_inputs = torch.cat([attack_embeds, defend_embeds, n_soldiers], dim=1)  # [num_actions, 2 * node_embed_dim + 1]
        logits = self.mlp(action_inputs).squeeze()  # [num_actions]
        
        return logits

class PlayerRL(Player):
    def __init__(self, name, model, device):
        super().__init__(name)
        self.model = model  
        self.experiences = []
        self.device = device

    def process_cards_phase(self):
       options = self.get_trade_in_options()
       if options:
           if self.game.log_all:   
            logging.info(f"\x1b[1m\nCards Phase - {self}\x1b[0m")
           self.game.trade_in_cards(self, options[0])
    
    def process_draft_phase(self):
        if self.game.log_all:
            logging.info(f"\x1b[1m\nDraft Phase - {self}\x1b[0m")
            logging.info(f"\x1b[33mUnassigned soldiers: {self.unassigned_soldiers}\x1b[0m")
        while self.unassigned_soldiers > 0:
            player_state = self.game.get_player_army_summary(self)
            country_selected = player_state[0][0] # country with highest threat ratio
            # assign one soldier to country before we re-evaluate the threat ratios
            self.game.assign_soldiers(self, country_selected, 1)

    def process_attack_phase(self):
        if self.game.log_all:
            logging.info(f"\x1b[1m\nAttack Phase - {self}\x1b[0m")
        
        num_soldiers_total = sum(c.army.n_soldiers for c in self.countries)
        max_attacks_per_round = min(25, max(1, num_soldiers_total - 18))
        game_won = False
        no_attack = True
        current_round_experiences = []

        attack_iter = 0
        while True:
            soldier_diffs = self.game.get_soldier_diffs(self)
            max_soldier_diff = max(soldier_diffs)
            if attack_iter != 0 and attack_iter > max_attacks_per_round and max_soldier_diff < 5:
                break

            node_features= self.game.get_game_state_encoded(self)
            attack_options_array = self.game.get_attack_options_encoded(self) # for valid action mask
            
            valid_action_mask = torch.tensor(attack_options_array, dtype=torch.bool).to(self.device)
            node_features_tensor = torch.tensor(node_features, dtype=torch.float32).to(self.device)
            edge_index_tensor = torch.tensor(self.game.edge_list_array, dtype=torch.long).to(self.device)

            logits = self.model(node_features_tensor, edge_index_tensor, self.game.action_lookup_table)
            
            # mask away invalid actions
            masked_logits = logits.clone()
            masked_logits[~valid_action_mask] = float('-inf')

            action_probs = F.softmax(masked_logits, dim=0)
            action_idx = torch.multinomial(action_probs, num_samples=1).item()
            attack_idx, defend_idx, n_soldiers = self.game.action_lookup_table[action_idx]
            attack_iter += 1

            # handle skip action
            if attack_idx == -1:
                break
            else:
                attack_country = self.game.countries[attack_idx]
                no_attack = False
                attack_country = self.game.countries[attack_idx]
                defend_country = self.game.countries[defend_idx]
                reward, game_won = self.game.attack(self, attack_country, defend_country, n_soldiers)

                current_round_experiences.append({
                    'node_features': node_features_tensor.cpu(),
                    'edge_index': edge_index_tensor.cpu(),
                    'valid_action_mask': valid_action_mask.cpu(),
                    'action_idx': action_idx,
                    'reward': reward,
                    'action_probs': action_probs.detach().cpu()
                })

                if game_won:
                    break
        
        if no_attack:
            current_round_experiences.append({
                    'node_features': node_features_tensor.cpu(),
                    'edge_index': edge_index_tensor.cpu(),
                    'valid_action_mask': valid_action_mask.cpu(),
                    'action_idx': action_idx,
                    'reward': -25, #sharp penatly for not making an attack in round
                    'action_probs': action_probs.detach().cpu()
                })
        
        self.experiences.extend(current_round_experiences)
        
    def process_fortify_phase(self):
        if self.game.log_all:
            logging.info(f"\x1b[1m\nFortify Phase - {self}\x1b[0m")
        
        destination_countries = set() # set of countries that have received fortify troops in this round
        num_soldiers_total = sum(c.army.n_soldiers for c in self.countries)
        max_fortify_moves = max(1, num_soldiers_total - 15)
        for fortify_iter in range(max_fortify_moves):
            fortify_options_ranked = self.game.get_fortify_options(self)
            
            fortify_options_ranked = [x for x in fortify_options_ranked if x[0] not in destination_countries]
            if len(fortify_options_ranked) == 0:
                break

            origin, dest, \
                origin_troop_diff, dest_troop_diff, \
                origin_n_soldiers, dest_n_soldiers = fortify_options_ranked[0]
            
            if origin_troop_diff == float('inf'):
                n_soldiers_move = max(1, (origin_n_soldiers-1) // 2)
            else:
                n_soldiers_move = 1
            
            self.game.fortify(self, origin, dest, n_soldiers_move)
            destination_countries.add(dest)

        self.game.reinforce(self)

    