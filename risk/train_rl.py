from risk.game import Game
from risk.player_heuristic import PlayerHeuristic
from risk.player_rl import PlayerRL, RiskGNN
from risk.player_random import PlayerRandom
import risk.logging_setup as logging_setup
import logging
import torch.optim as optim
import torch
import torch.nn.functional as F
from tqdm import tqdm
import torch.nn.utils
import torch.optim.lr_scheduler 
import pickle
from datetime import datetime

def dump_eval_results(eval_results):
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M")
    with open(f'risk/eval_results/eval_results_{timestamp}.pk', 'wb') as f:
        pickle.dump(eval_results, f)

def save_model_checkpoint(model, optimizer, episode):
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M")
    checkpoint = {
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'episode': episode,
    }
    torch.save(checkpoint, f'risk/model_checkpoints/rl_model_checkpoint_episode_{episode}_{timestamp}.pt')

def load_model_checkpoint(filepath, model, optimizer, device):
    checkpoint = torch.load(filepath, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    episode = checkpoint['episode']
    return model, optimizer, episode

# evaluate model against stronger opponentes
def eval_model(model, device, n_episode, num_games=100):
    logging.info(f"Evaluating model after {n_episode} training episodes")

    num_rounds_ls = [] # to get distribution of game duration
    game_wins = [] # RL won/lost game int bool (0, 1)
    game_tied = [] # Game ended in tie int bool (0, 1) 
    
    for _ in tqdm(range(num_games), desc="Evaluating RL model"):
        # tweak this, try different configurations
        players = [
                PlayerRandom("Player Random 1"),
                PlayerRL("Player RL 2", model, device),
                PlayerRandom("Player Random 3"),
                PlayerRandom("Player Random 4"),
                PlayerRandom("Player Random 5"),
            ]
        
        game = Game(players, display_map=False, log_all=False, eval_log=True)
        num_rounds_game, rl_won, game_tie = game.gameplay_loop()
        
        num_rounds_ls.append(num_rounds_game)
        game_wins.append(rl_won)
        game_tied.append(game_tie)
        game_wins.append(rl_won)
    
    logging.info(f"Current Eval tie rate after {n_episode} training episodes: {round(sum(game_tied)/num_games, 4)}")
    logging.info(f"Current Eval win rate after {n_episode} training episodes: {round(sum(game_wins)/num_games, 4)}")
    
    return num_rounds_ls, game_wins, game_tied

    
def train(num_episodes=20_000, eval_interval=1000, checkpoint_path=None):
    logging_setup.init_logging(name='rl_training_new_log')
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logging.info(f"Running torch on device: {device}")
    
    model = RiskGNN(
            in_channels_node=14, # number of features in node embeddings 
            hidden_dim=64, 
            num_actions=493 # number of possible attacks
        ).to(device)
    optimizer = optim.Adam(model.parameters(), lr=1e-4) # TODO Tune lr
    
    start_episode = 0
    if checkpoint_path:
        model, optimizer, start_episode = load_model_checkpoint(checkpoint_path, model, optimizer, device)
        logging.info(f"Resuming training from episode {start_episode}")
    

    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=1000)
    
    eval_results = []
    for i in tqdm(range(num_episodes), desc="Training RL model"):
        # tweak this, try different configurations, should we use majority RL players?
        # was using only random opponents, that way the game ends in tie too often
        players = [
            PlayerRandom("Player Random 1"),
            PlayerRandom("Player Random 2"),
            PlayerRL("Player RL 3", model, device),
            PlayerRL("Player RL 4", model, device),
            PlayerHeuristic("Player Heuristic 5"),
        ]
        
        game = Game(players, display_map=False, log_all=False, eval_log=False)
        game.gameplay_loop()
                    
        all_experiences = []
        # note that at end of game, the eliminated list includes all players, including winner
        for player in game.players_eliminated: 
            if isinstance(player, PlayerRL):
                all_experiences.extend(player.experiences)
        
        train_model(model, optimizer, all_experiences, game.action_lookup_table, device)
        
        if (i + 1) % eval_interval == 0:
            # eval model
            eval_results.append(eval_model(model, device, n_episode=i+1))
        
        if (i + 1) % 1000 == 0:
            save_model_checkpoint(model, optimizer, i + 1 + start_episode)
    
    save_model_checkpoint(model, optimizer, num_episodes + start_episode)
    dump_eval_results(eval_results)

def train_model(model, optimizer, experiences, action_lookup_table, device):
    states = []
    edge_indices = []
    valid_action_masks = []
    action_indices = []
    rewards = []
    
    for exp in experiences:
        states.append(exp['node_features'].to(device))
        edge_indices.append(exp['edge_index'].to(device))
        valid_action_masks.append(exp['valid_action_mask'].to(device))
        action_indices.append(exp['action_idx'])
        rewards.append(exp['reward'])
    
    rewards = compute_discounted_rewards(rewards, gamma=0.99)
    loss = compute_policy_loss(model, states, edge_indices, valid_action_masks, action_indices, rewards, action_lookup_table)
    
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

def compute_policy_loss(model, states, edge_indices, valid_action_masks, action_indices, rewards, action_lookup_table):
    total_loss = 0.0
    device = states[0].device
    edge_index = edge_indices[0] 
    
    rewards_tensor = torch.tensor(rewards, dtype=torch.float, device=device)
    normalized_rewards = (rewards_tensor - rewards_tensor.mean()) / (rewards_tensor.std() + 1e-8)
    
    for state, valid_mask, action_idx, reward in zip(states, valid_action_masks, action_indices, normalized_rewards):
        logits = model(state, edge_index, action_lookup_table)
        
        masked_logits = logits.clone()
        masked_logits[~valid_mask] = float('-inf')
    
        probs = F.softmax(masked_logits, dim=0)
        selected_prob = probs[action_idx]
        log_prob = torch.log(selected_prob + 1e-8)
        total_loss += -log_prob * reward # policy gradient ascent update
    
    return total_loss
