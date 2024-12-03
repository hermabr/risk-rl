from risk.country import *
from risk.player import Player
import logging

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import NNConv

class RiskGNN(nn.Module):
    def __init__(self, in_channels_node, in_channels_edge, hidden_dim, num_actions):
        super(RiskGNN, self).__init__()
        self.node_embed_dim = hidden_dim

        self.edge_network1 = nn.Sequential(
            nn.Linear(in_channels_edge, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, in_channels_node * hidden_dim)  # Output size: [num_edges, 3 * 64]
        )

        self.edge_network2 = nn.Sequential(
            nn.Linear(in_channels_edge, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim * hidden_dim)  # Output size: [num_edges, 64 * 64]
        )

        self.conv1 = NNConv(in_channels_node, hidden_dim, self.edge_network1, aggr='mean')
        self.conv2 = NNConv(hidden_dim, hidden_dim, self.edge_network2, aggr='mean')
        self.action_head = ActionHead(hidden_dim, num_actions)

    def forward(self, x, edge_index, edge_attr, action_lookup_table):
        # x: Node features [num_nodes, in_channels_node]
        # edge_index: Edge indices [2, num_edges]
        # edge_attr: Edge features [num_edges, in_channels_edge]

        # apply graph conv layers
        x = F.relu(self.conv1(x, edge_index, edge_attr))
        x = F.relu(self.conv2(x, edge_index, edge_attr))

        logits = self.action_head(x, action_lookup_table)
        return logits
    
class ActionHead(nn.Module):
    def __init__(self, node_embed_dim, num_actions):
        super(ActionHead, self).__init__()
        self.node_embed_dim = node_embed_dim
        self.num_actions = num_actions

        self.skip_attack_embed = nn.Parameter(torch.zeros(node_embed_dim))
        self.skip_defend_embed = nn.Parameter(torch.zeros(node_embed_dim))

        # Learnable embeddings for skip action
        self.skip_attack_embed = nn.Parameter(torch.zeros(node_embed_dim))
        self.skip_defend_embed = nn.Parameter(torch.zeros(node_embed_dim))

        self.mlp = nn.Sequential(
            nn.Linear(2 * node_embed_dim + 1, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )

    def forward(self, node_embeddings, action_lookup_table):
        attack_embeds = []
        defend_embeds = []
        n_soldiers_list = []

        for attack_idx, defend_idx, n_soldiers in action_lookup_table:
            if attack_idx != -1:

                attack_embeds.append(node_embeddings[attack_idx])
                defend_embeds.append(node_embeddings[defend_idx])
            else:
                attack_embeds.append(self.skip_attack_embed)
                defend_embeds.append(self.skip_defend_embed)
            
            n_soldiers_list.append(n_soldiers)

        attack_embeds = torch.stack(attack_embeds)  # [num_actions, node_embed_dim]
        defend_embeds = torch.stack(defend_embeds)  # [num_actions, node_embed_dim]
        device = attack_embeds.device
        
        n_soldiers_tensor = torch.tensor(n_soldiers_list, dtype=torch.float32).unsqueeze(1).to(device)  # [num_actions, 1]

        # Concatenate embeddings and n_soldiers
        action_inputs = torch.cat([attack_embeds, defend_embeds, n_soldiers_tensor], dim=1)  # [num_actions, 2 * node_embed_dim + 1]

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
        max_attacks_per_round = 15
        game_won = False
        no_attack = True
        for _ in range(max_attacks_per_round):
            if self.game.num_players == 1:
                break
            
            node_features, edge_features = self.game.get_game_state_encoded(self)
            attack_options_array = self.game.get_attack_options_encoded(self)
            
            valid_action_mask = torch.tensor(attack_options_array, dtype=torch.bool).to(self.device)
            node_features_tensor = torch.tensor(node_features, dtype=torch.float32).to(self.device)
            edge_index_tensor = torch.tensor(self.game.edge_list_array, dtype=torch.long).to(self.device)
            edge_attr_tensor = torch.tensor(edge_features, dtype=torch.float32).to(self.device)

            logits = self.model(node_features_tensor, edge_index_tensor, edge_attr_tensor, self.game.action_lookup_table)
            
            # mask away invalid actions
            masked_logits = logits.clone()
            masked_logits[~valid_action_mask] = float('-inf')

            action_probs = F.softmax(masked_logits, dim=0)
            action_idx = torch.multinomial(action_probs, num_samples=1).item()

            attack_idx, defend_idx, n_soldiers = self.game.action_lookup_table[action_idx]
            
            # Handle skip action
            if attack_idx != -1:
                attack_country = self.game.countries[attack_idx]
                no_attack = False
                attack_country = self.game.countries[attack_idx]
                defend_country = self.game.countries[defend_idx]
                reward = self.game.attack(self, attack_country, defend_country, n_soldiers)

                self.experiences.append({
                    'node_features': node_features_tensor.cpu(),
                    'edge_index': edge_index_tensor.cpu(),
                    'edge_attr': edge_attr_tensor.cpu(),
                    'valid_action_mask': valid_action_mask.cpu(),
                    'action_idx': action_idx,
                    'reward': reward,
                    'action_probs': action_probs.detach().cpu()
                })

        if not game_won and no_attack:
            self.experiences.append({
                    'node_features': node_features_tensor.cpu(),
                    'edge_index': edge_index_tensor.cpu(),
                    'edge_attr': edge_attr_tensor.cpu(),
                    'valid_action_mask': valid_action_mask.cpu(),
                    'action_idx': action_idx,
                    'reward': -5, # negative reward for newer attacking during phase
                    'action_probs': action_probs.detach().cpu()
                })


    def process_fortify_phase(self):
        if self.game.log_all:
            logging.info(f"\x1b[1m\nFortify Phase - {self}\x1b[0m")
        
        destination_countries = set() # set of countries that have received fortify troops in this round
        max_fortify_moves = 10 # TODO: determine what is sensible here
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

    