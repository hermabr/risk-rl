from risk.game import Game
from risk.player_heuristic import PlayerHeuristic
from risk.player_rl import PlayerRL, RiskGNN
import risk.logging_setup as logging_setup
import logging
import torch.optim as optim
import torch
import torch.nn.functional as F
from tqdm import tqdm
import torch.nn.utils
import torch.optim.lr_scheduler 

def test_decode_attack_options(game: Game):
    for attack_options in range(game.total_attack_options_cnt):
        attack_country, defend_country, n_soldiers = game.decode_attack_option(attack_options)
        logging.info(f"{attack_country}, {defend_country}, {n_soldiers}")

def save_model_checkpoint(model, episode):
    torch.save(model.state_dict(), f'risk/model_checkpoints/rl_model_checkpoint_episode_{episode}.pt')

def train(num_episodes=10_000):
    logging_setup.init_logging(name='rl_training_log')
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logging.info(f"Running torch on device: {device}")
    
    model = RiskGNN(
        in_channels_node=3, 
        in_channels_edge=5, 
        hidden_dim=64, 
        num_actions=493 # number of possible attacks
    ).to(device) 
    
    optimizer = optim.Adam(model.parameters(), lr=1e-4)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10000, gamma=0.1)
    
    num_rounds_ls = [] # to get distribution of game duration
    win_rates = []
    rl_wins = 0
    game_cnt = 0

    for i in tqdm(range(num_episodes), desc="Training RL model"):
        logging.info(f"Episode: {i+1} of {num_episodes}")
        players = [
            PlayerHeuristic("Player 1"),
            PlayerRL("Player RL 2", model, device),
            PlayerHeuristic("Player 3"),
            PlayerHeuristic("Player 4"),
            PlayerHeuristic("Player 5")
        ]
        game = Game(players, display_map=False, log_all=False)
        
        num_rounds_game, rl_won = game.gameplay_loop()
        if num_rounds_game != 0:
            game_cnt += 1
            rl_wins += rl_won
            win_rate = rl_wins/game_cnt
            logging.info(f"Current win rate: {win_rate}")
            win_rates.append(win_rate)
            num_rounds_ls.append(num_rounds_game)
            
        all_experiences = []
        for player in game.players_eliminated:
            if isinstance(player, PlayerRL):
                all_experiences.extend(player.experiences)
        
        train_model(model, optimizer, all_experiences, game.action_lookup_table, device)
    

    
    save_model_checkpoint(model, num_episodes) # TODO maybe save at intervals?

def train_model(model, optimizer, experiences, action_lookup_table, device):
    states = []
    edge_indices = []
    edge_attrs = []
    valid_action_masks = []
    action_indices = []
    rewards = []
    
    for exp in experiences:
        states.append(exp['node_features'].to(device))
        edge_indices.append(exp['edge_index'].to(device))
        edge_attrs.append(exp['edge_attr'].to(device))
        valid_action_masks.append(exp['valid_action_mask'].to(device))
        action_indices.append(exp['action_idx'])
        rewards.append(exp['reward'])
    
    rewards = compute_discounted_rewards(rewards, gamma=0.99)
    loss = compute_policy_loss(model, states, edge_indices, edge_attrs, valid_action_masks, action_indices, rewards, action_lookup_table)
    
    optimizer.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
    optimizer.step()

def compute_discounted_rewards(rewards, gamma):
    discounted_rewards = []
    R = 0
    for r in reversed(rewards):
        R = r + gamma * R
        discounted_rewards.insert(0, R)
    return discounted_rewards

def compute_policy_loss(model, states, edge_indices, edge_attrs, valid_action_masks, action_indices, rewards, action_lookup_table):
    total_loss = 0.0
    device = states[0].device
    edge_index = edge_indices[0] 
    
    rewards_tensor = torch.tensor(rewards, dtype=torch.float, device=device)
    normalized_rewards = (rewards_tensor - rewards_tensor.mean()) / (rewards_tensor.std() + 1e-8)
    
    for state, edge_attr, valid_mask, action_idx, reward in zip(states, edge_attrs, valid_action_masks, action_indices, normalized_rewards):
        logits = model(state, edge_index, edge_attr, action_lookup_table)
        
        masked_logits = logits.clone()
        masked_logits[~valid_mask] = float('-inf')
    
        probs = F.softmax(masked_logits, dim=0)
        selected_prob = probs[action_idx]
        log_prob = torch.log(selected_prob + 1e-8)
        total_loss += -log_prob * reward
    
    return total_loss



