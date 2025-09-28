import sys
import gc
import os
import json
import random
import multiprocessing 
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tensorflow as tf
from datetime import datetime
from pathlib import Path
from typing import List, Any, Dict
from multiprocessing import Manager

# Suppress TensorFlow logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="keras.saving")

from data.forecasting.data_functions import load_data_from_mongodb
from data.forecasting.constants import (

    ENABLE_TIME_ENCODING,
    ENABLE_INSTR_DAY,
    ENABLE_EVENT_ENCODING,
    GENETIC_LOG
)


# Genetic algorithm parameters
POPULATION_SIZE = 128 # Number of individuals in the population
GENERATIONS = 25 # Number of generations to evolve
ELITES_SIZE = 4 # Number of top individuals to carry over unchanged to the next generation
NEW_INDIVIDUALS_PER_GEN_RATIO = 0.1  # Ratio of completely random individuals to children of last generation, 0 for none
ADAPTIVE_CROSSOVER_RATE = 0.7
INITIAL_MUTATION_RATE = 0.5
FINAL_MUTATION_RATE = 0.05
POPS_PER_TORNAMENT = 4  # Number of individuals competing in each tournament

# Run parameters
TEST_SPLIT = 0.975
TRAINING_EPOCHS = 50 

# other parameters
MULTIPROCESSING_MAX_PROCESSES = 6  # Max number of parallel processes for fitness evaluation

# Update the search space for hyperparameters
HYPERPARAMETER_SPACE = {
    "lstm_neurons_list": range(16, 512, 1),
    "lstm_layers": [1, 2, 3, 4, 5, 6],
    "dropout": (0.05, 0.9),
    "learning_rate": (1e-5, 1e-3),
    "activation": [ "celu", "elu", "gelu", "hard_sigmoid", "hard_tanh", "hard_silu","leaky_relu", "linear", "mish", "relu", "silu"],
    "optimizer": ["nadam", "adam", "rmsprop", "lion", "adamax", "adamw"],
    "batch_size": [256, 512, 1024, 2048]
}

# pre-define good starting pops
starting_pops = [
    # # South
    # {'lstm_neurons_list': [198, 345, 251, 367], 'dropout': 0.2604909306814078, 'learning_rate': 0.00019687721787212608, 'activation': 'hard_tanh', 'optimizer': 'nadam', 'batch_size': 512, 'lstm_layers': 4}, #Loss: 0.001492829411290586
    # {'lstm_neurons_list': [349, 209, 405, 276], 'dropout': 0.21966249523451964, 'learning_rate': 0.0001149133286221292, 'activation': 'celu', 'optimizer': 'lion', 'batch_size': 256, 'lstm_layers': 3}, # Loss: 0.001130951102823019
    # {'lstm_neurons_list': [511, 236, 260], 'dropout': 0.46926611139688446, 'learning_rate': 0.003780982030266334, 'activation': 'sigmoid', 'optimizer': 'nadam', 'batch_size': 1024, 'lstm_layers': 3}, # Loss: 0.0016010220861062407
    # {'lstm_neurons_list': [144, 303, 428, 369], 'dropout': 0.2717238359847232, 'learning_rate': 0.0010100765283741343, 'activation': 'hard_tanh', 'optimizer': 'adamax', 'batch_size': 512, 'lstm_layers': 3}, Loss: 0.0025257107336074114
    # # West
    # {'lstm_neurons_list': [141, 499, 448], 'dropout': 0.45827972302256537, 'learning_rate': 0.0039749877186755975, 'activation': 'sigmoid', 'optimizer': 'nadam', 'batch_size': 512, 'lstm_layers': 3}, # Loss: 0.0013190264580771327
    # {'lstm_neurons_list': [150, 105, 289, 329, 474], 'dropout': 0.6090342302354329, 'learning_rate': 0.0003940610980452166, 'activation': 'hard_sigmoid', 'optimizer': 'adam', 'batch_size': 512, 'lstm_layers': 5}, Loss: 0.0010854111751541495
    # # South Campus
    # {'lstm_neurons_list': [342, 511], 'dropout': 0.4051419432780984, 'learning_rate': 0.00020582730403405803, 'activation': 'silu', 'optimizer': 'lion', 'batch_size': 256, 'lstm_layers': 2}, # Loss: 0.004495117347687483
    # {'lstm_neurons_list': [129, 123, 413, 421, 456], 'dropout': 0.3690355975090591, 'learning_rate': 0.0021108835847791053, 'activation': 'linear', 'optimizer': 'adamax', 'batch_size': 1024, 'lstm_layers': 5}, # Loss: 0.004978095181286335 w/o t
    # {'lstm_neurons_list': [73, 212, 338, 489], 'dropout': 0.5633597438239422, 'learning_rate': 0.0024480537376972418, 'activation': 'celu', 'optimizer': 'nadam', 'batch_size': 256, 'lstm_layers': 4}, # Loss: 0.0028183283284306526 
    # # North
    # {'lstm_neurons_list': [345, 361, 393, 423], 'dropout': 0.5877143299073334, 'learning_rate': 0.0019881450310899862, 'activation': 'sigmoid', 'optimizer': 'nadam', 'batch_size': 512, 'lstm_layers': 4}, # Loss: 0.0016761806327849627
]

# Define global variable for extra_long_data
EXTRA_LONG_DATA = 0
if ENABLE_INSTR_DAY:
    EXTRA_LONG_DATA += 2
if ENABLE_TIME_ENCODING:
    EXTRA_LONG_DATA += 10
if ENABLE_EVENT_ENCODING:
    EXTRA_LONG_DATA += 4

def initialize_population() -> List[Dict[str, Any]]:
    """Randomly initialize the population."""

    population = []
    for pop in starting_pops:
        population.append(pop)
    for _ in range(POPULATION_SIZE-len(starting_pops)):
        layers = random.choice(HYPERPARAMETER_SPACE["lstm_layers"])
        neuron_layers = []
        for _ in range(0,layers):
            neuron_layers.append(random.choice(HYPERPARAMETER_SPACE["lstm_neurons_list"]))

        individual = {
            "lstm_neurons_list": neuron_layers,
            "dropout"       : random.uniform(*HYPERPARAMETER_SPACE["dropout"]),
            "learning_rate" : random.uniform(*HYPERPARAMETER_SPACE["learning_rate"]),
            "activation"    : random.choice(HYPERPARAMETER_SPACE["activation"]),
            "optimizer"     : random.choice(HYPERPARAMETER_SPACE["optimizer"]),
            "batch_size"    : random.choice(HYPERPARAMETER_SPACE["batch_size"]),
            "lstm_layers": layers,
        }
        population.append(individual)
    return population


# Update evaluate_fitness_worker to directly return the loss instead of using a queue
def evaluate_fitness_worker(individual, garage, data):
    import tensorflow as tf
    from data.forecasting.keras_model_file import build_model
    from data.forecasting.long_term_model import train_long_model_with_generator
    from data.forecasting.constants import GARAGE_NAMES, LONG_SEQ, LONG_FUTURE_STEPS
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    # Ensure lstm_neurons_list is always a list
    if isinstance(individual["lstm_neurons_list"], int):
        individual["lstm_neurons_list"] = [individual["lstm_neurons_list"]]

    print(f"Evaluating model for garage: {garage}")
    print("Hyperparameters:")
    for key, value in individual.items():
        print(f"  {key}: {value}")

    # Select optimizer
    optimizer = None
    if individual["optimizer"] == "adam":
        optimizer = tf.keras.optimizers.Adam(learning_rate=individual["learning_rate"])
    elif individual["optimizer"] == "adamw":
        optimizer = tf.keras.optimizers.AdamW(learning_rate=individual["learning_rate"])
    elif individual["optimizer"] == "nadam":
        optimizer = tf.keras.optimizers.Nadam(learning_rate=individual["learning_rate"])
    elif individual["optimizer"] == "rmsprop":
        optimizer = tf.keras.optimizers.RMSprop(learning_rate=individual["learning_rate"])
    elif individual["optimizer"] == "lion":
        optimizer = tf.keras.optimizers.Lion(learning_rate=individual["learning_rate"])
    elif individual["optimizer"] == "adamax":
        optimizer = tf.keras.optimizers.Adamax(learning_rate=individual["learning_rate"])
    elif individual["optimizer"] == "adadelta":
        optimizer = tf.keras.optimizers.Adadelta(learning_rate=individual["learning_rate"])

    model = build_model(
        lstm_neurons_list=individual["lstm_neurons_list"],
        dropout=individual["dropout"],
        seq_size=LONG_SEQ,
        activation=individual["activation"],
        n_feature=4 + EXTRA_LONG_DATA,
        future_steps=LONG_FUTURE_STEPS,
        garage_no=GARAGE_NAMES.index(garage),
        optimizer=optimizer)

    # Train the model and get the validation loss
    try:
        val_loss = train_long_model_with_generator(
            model=model,
            batch_size=individual["batch_size"],
            future_steps=LONG_FUTURE_STEPS,
            test_split=TEST_SPLIT,
            seq_size=LONG_SEQ,
            name=f"temp_model_{garage}",
            training_epochs=TRAINING_EPOCHS,
            data=data)
    except Exception as e:
        print(f"Error during training: {e}")
        return float('inf')  # Assign a high loss to indicate failure

    return val_loss[0]


# Update worker_process to use the new evaluate_fitness_worker
def worker_process(individual, garage, data, results, index):
    import tensorflow as tf
    tf.config.optimizer.set_jit(True)  # Enable XLA JIT compilation
    try:
        val_loss = evaluate_fitness_worker(individual, garage, data)
        results[index] = val_loss
    except Exception as e:
        print(f"Error in worker_process: {e}")
        results[index] = float('inf')  # Assign a high loss to indicate failure

# Update evaluate_fitness to use the new evaluate_fitness_worker
def evaluate_fitness(individual: Dict[str, Any], garage: str, data: np.ndarray) -> float:
    
    # Create a multiprocessing context
    ctx = multiprocessing.get_context("spawn")
    manager = Manager()
    results = manager.list([None])  # Shared list to store the result

    # Start the worker process
    process = ctx.Process(target=worker_process, args=(individual, garage, data, results, 0))
    process.start()
    process.join(timeout=60)
    if process.is_alive():
        print(f"Process {process.pid} failed to terminate.")
        process.terminate()

    # Retrieve the validation loss from the shared list
    val_loss = results[0]

    return val_loss


def evaluate_fitness_parallel_v2(population: List[Dict[str, Any]], garage: str, data: np.ndarray) -> List[float]:
    """Evaluate the fitness of the entire population in parallel using subprocesses with a limit on the number of active processes."""
    ctx = multiprocessing.get_context("spawn")
    manager = Manager()
    results = manager.list([None] * len(population))  # Shared list to store results
    processes = []

    for index, individual in enumerate(population):
        # Wait for an available slot if the number of active processes reaches the limit
        while len([p for p in processes if p.is_alive()]) >= MULTIPROCESSING_MAX_PROCESSES:
            for process in processes:
                if not process.is_alive():
                    process.join()  # Ensure completed processes are joined

        # Start a new process
        process = ctx.Process(target=worker_process, args=(individual, garage, data, results, index))
        processes.append(process)
        process.start()

    # Ensure all processes are joined after starting
    for process in processes:
        process.join()

    return list(results)


# Select parents using tournament selection
def select_parents(population: List[Dict[str, Any]], fitness_scores: List[float]) -> List[Dict[str, Any]]:
    selected = []
    for _ in range(POPULATION_SIZE // 2):
        tournament = random.sample(list(zip(population, fitness_scores)), k=POPS_PER_TORNAMENT)
        winner = min(tournament, key=lambda x: x[1])  # Select the individual with the lowest loss
        selected.append(winner[0])
    return selected

# Perform crossover between two parents
def crossover(parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Dict[str, Any]:
    offspring = {}
    for key in parent1.keys():
        if key == "lstm_neurons_list":
            parent1_layers = parent1[key]
            parent2_layers = parent2[key]
            max_layers = max(len(parent1_layers), len(parent2_layers))
            offspring_layers = []
            for i in range(max_layers):
                if i < len(parent1_layers) and i < len(parent2_layers):
                    avg_neurons = int((parent1_layers[i] + parent2_layers[i]) / 2)
                    # Clamp to bounds
                    min_n, max_n = min(HYPERPARAMETER_SPACE["lstm_neurons_list"]), max(HYPERPARAMETER_SPACE["lstm_neurons_list"])
                    avg_neurons = max(min_n, min(max_n, avg_neurons))
                    offspring_layers.append(avg_neurons)
                elif i < len(parent1_layers):
                    n = parent1_layers[i]
                    min_n, max_n = min(HYPERPARAMETER_SPACE["lstm_neurons_list"]), max(HYPERPARAMETER_SPACE["lstm_neurons_list"])
                    n = max(min_n, min(max_n, n))
                    offspring_layers.append(n)
                elif i < len(parent2_layers):
                    n = parent2_layers[i]
                    min_n, max_n = min(HYPERPARAMETER_SPACE["lstm_neurons_list"]), max(HYPERPARAMETER_SPACE["lstm_neurons_list"])
                    n = max(min_n, min(max_n, n))
                    offspring_layers.append(n)
            offspring[key] = offspring_layers
        # Clamp to bounds for dropout
        elif key == "dropout":
            min_d, max_d = HYPERPARAMETER_SPACE["dropout"]
            val = random.choice([parent1[key], parent2[key]])
            offspring[key] = max(min_d, min(max_d, val))
        # Clamp to bounds for learning rate
        elif key == "learning_rate":
            min_lr, max_lr = HYPERPARAMETER_SPACE["learning_rate"]
            val = random.choice([parent1[key], parent2[key]])
            offspring[key] = max(min_lr, min(max_lr, val))
        # Clamp to bounds for batch size
        elif key == "batch_size":
            val = random.choice([parent1[key], parent2[key]])
            allowed = HYPERPARAMETER_SPACE["batch_size"]
            offspring[key] = val if val in allowed else allowed[0]
        # Handle lstm layers
        elif key == "lstm_layers":
            offspring[key] = random.choice([parent1[key], parent2[key]])
        # Default case
        else:
            val = random.choice([parent1[key], parent2[key]])
            allowed = HYPERPARAMETER_SPACE[key]
            offspring[key] = val if val in allowed else allowed[0]

    return offspring


# Mutate an individual
def mutate(individual: Dict[str, Any], mutation_rate: float = 0.5) -> Dict[str, Any]:
    if random.random() < mutation_rate:
        key = random.choice(list(HYPERPARAMETER_SPACE.keys()))
        if key == "lstm_neurons_list":
            min_n, max_n = min(HYPERPARAMETER_SPACE["lstm_neurons_list"]), max(HYPERPARAMETER_SPACE["lstm_neurons_list"])
            new_layers = []
            for n in individual[key]:
                # Change by +/- (10% to 50%) depending on mutation rate
                max_change = 0.4 * mutation_rate
                delta = int(n * random.uniform(-max_change, max_change))
                new_n = max(min_n, min(max_n, n + delta))
                new_layers.append(new_n)
            individual[key] = new_layers
            individual["lstm_layers"] = len(new_layers)
        elif key == "dropout":
            val = individual[key]
            min_d, max_d = HYPERPARAMETER_SPACE["dropout"]
            max_change = 0.4 * mutation_rate
            delta = val * random.uniform(-max_change, max_change)
            new_val = max(min_d, min(max_d, val + delta))
            individual[key] = new_val
        elif key == "learning_rate":
            val = individual[key]
            min_lr, max_lr = HYPERPARAMETER_SPACE["learning_rate"]
            max_change = 0.4 * mutation_rate
            delta = val * random.uniform(-max_change, max_change)
            new_val = max(min_lr, min(max_lr, val + delta))
            individual[key] = new_val
        elif key == "batch_size":
            allowed = HYPERPARAMETER_SPACE["batch_size"]
            val = random.choice(allowed)
            individual[key] = val if val in allowed else allowed[0]
        elif key == "lstm_layers":
            allowed = HYPERPARAMETER_SPACE["lstm_layers"]
            layers = random.choice(allowed)
            individual[key] = layers
            old_layers = individual["lstm_neurons_list"]
            min_n, max_n = min(HYPERPARAMETER_SPACE["lstm_neurons_list"]), max(HYPERPARAMETER_SPACE["lstm_neurons_list"])
            if layers < len(old_layers):
                individual["lstm_neurons_list"] = [max(min_n, min(max_n, n)) for n in old_layers[:layers]]
            else:
                individual["lstm_neurons_list"] = [max(min_n, min(max_n, n)) for n in old_layers] + [random.choice(HYPERPARAMETER_SPACE["lstm_neurons_list"]) for _ in range(layers - len(old_layers))]
        else:
            allowed = HYPERPARAMETER_SPACE[key]
            val = random.choice(allowed)
            individual[key] = val
    return individual

# Main genetic algorithm function
def genetic_algorithm(garage: str, data: np.ndarray):
    """Run the genetic algorithm to optimize hyperparameters for a specific garage and save population hyperparameters for each generation."""

    # Clear the best models file at the start of a new run
    with open(f"{GENETIC_LOG}/best_model_{garage_name}.txt", "w") as f:
        f.write("Best Models per Generation\n")

    population = initialize_population()
    best_models = []  # To store the best model of each generation
    avg_val_losses = []  # To store the average validation loss of each generation
    lowest_val_losses = []  # To store the lowest validation loss of each generation
    elites = []  # To store the best-performing models across all generations
    elite_losses = []  # Store their losses

    # Adaptive crossover rate based on fitness
    mutation_decay = (INITIAL_MUTATION_RATE - FINAL_MUTATION_RATE) / GENERATIONS

    for generation in range(GENERATIONS):
        print(f"Generation {generation + 1}")
        # Simulated annealing: decrease mutation rate over time
        mutation_rate = max(FINAL_MUTATION_RATE, INITIAL_MUTATION_RATE - mutation_decay * generation)

        # Evaluate fitness for the population serially
        fitness_scores = evaluate_fitness_parallel_v2(population, garage, data)

        # Remove any individuals with non-float fitness scores
        valid_population_scores = [(ind, score) for ind, score in zip(population, fitness_scores) if isinstance(score, float)]

        # Sort population by fitness
        sorted_population_scores = sorted(valid_population_scores, key=lambda x: x[1])
        population = [ind for ind, score in sorted_population_scores]
        fitness_scores = [score for ind, score in sorted_population_scores]

        # Update elites: keep only the best ELITES_SIZE models ever seen
        if ELITES_SIZE > 0:
            for ind, loss in zip(population, fitness_scores):
                if len(elites) < ELITES_SIZE:
                    elites.append(ind)
                    elite_losses.append(loss)
                else:
                    # If this model is better than the worst elite, replace it
                    worst_elite_idx = elite_losses.index(max(elite_losses))
                    if loss < elite_losses[worst_elite_idx]:
                        elites[worst_elite_idx] = ind
                        elite_losses[worst_elite_idx] = loss

        # Select parents (include current elites if any)
        if ELITES_SIZE > 0:
            selected_parents = select_parents(population, fitness_scores) + elites
        else:
            selected_parents = select_parents(population, fitness_scores)
        
        # -- NEXT GENERATION --
        next_generation = []

        # Add completely random individuals to maintain diversity
        if NEW_INDIVIDUALS_PER_GEN_RATIO != 0:
            num_random_individuals = int(POPULATION_SIZE // (1/NEW_INDIVIDUALS_PER_GEN_RATIO))
            for _ in range(num_random_individuals):
                layers = random.choice(HYPERPARAMETER_SPACE["lstm_layers"])
                neuron_layers = [random.choice(HYPERPARAMETER_SPACE["lstm_neurons_list"]) for _ in range(layers)]
                batch_size = random.choice(HYPERPARAMETER_SPACE["batch_size"])
                random_individual = {
                    "lstm_neurons_list": neuron_layers,
                    "dropout": random.uniform(*HYPERPARAMETER_SPACE["dropout"]),
                    "learning_rate": random.uniform(*HYPERPARAMETER_SPACE["learning_rate"]),
                    "activation": random.choice(HYPERPARAMETER_SPACE["activation"]),
                    "optimizer": random.choice(HYPERPARAMETER_SPACE["optimizer"]),
                    "batch_size": batch_size,
                    "lstm_layers": layers,
                }
                next_generation.append(random_individual)

        while len(next_generation) < POPULATION_SIZE:
            parent1, parent2 = random.sample(selected_parents, 2)
            # Adaptive crossover rate
            if random.random() < ADAPTIVE_CROSSOVER_RATE:
                offspring = crossover(parent1, parent2)
            else:
                offspring = random.choice([parent1, parent2])
            offspring = mutate(offspring, mutation_rate)
            next_generation.append(offspring)

        population = next_generation

        # Calculate and store average validation loss
        avg_val_loss = sum(fitness_scores) / len(fitness_scores)
        avg_val_losses.append(avg_val_loss)

        # Find the best model of the generation
        best_model, best_loss = sorted_population_scores[0]
        best_models.append(best_model)

        # Store the lowest validation loss of the generation
        lowest_val_losses.append(best_loss)

        # Log the best model and its loss to a text file
        with open(f"{GENETIC_LOG}/best_model_{garage_name}.txt", "a") as f:
            f.write(f"Generation {generation + 1}: {best_model}, Loss: {best_loss}\n")

        # Append each model's hyperparameters and val_loss to a persistent database file
        from datetime import datetime
        finished_time = datetime.now().isoformat()
        history_path = "population_history.json"
        # Load existing history if present
        if os.path.exists(history_path):
            with open(history_path, "r") as f:
                history = json.load(f)
        else:
            history = []

        # Append new entries for this generation
        for ind, val_loss in zip(population, fitness_scores):
            entry = dict(ind)
            entry["val_loss"] = val_loss
            entry["generation"] = generation
            entry["finished_time"] = finished_time
            entry["garage"] = garage
            history.append(entry)

        # Save updated history
        try:
            with open(history_path, "w") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"Error writing to history file: {e}")

        # Plot average and lowest validation loss per generation (updated every generation)
        plt.figure(figsize=(12, 6))
        plt.plot(range(1, len(avg_val_losses) + 1), avg_val_losses, marker="o", label="Average Loss")
        plt.plot(range(1, len(lowest_val_losses) + 1), lowest_val_losses, marker="x", label="Lowest Loss")
        plt.title("Validation Loss per Generation")
        plt.xlabel("Generation")
        plt.ylabel("Validation Loss")
        plt.legend()
        plt.grid(True)
        plt.savefig(f"{GENETIC_LOG}/generation_{garage_name}.svg")
        plt.close()

        # Clear TensorFlow session and collect garbage to prevent memory leaks
        tf.keras.backend.clear_session()
        gc.collect()

    # Return the best individual from the final generation
    if ELITES_SIZE > 0 and elites:
        best_elite_idx = elite_losses.index(min(elite_losses))
        best_individual = elites[best_elite_idx]
    else:
        best_individual = best_models[-1]
    print("Best hyperparameters:", best_individual)
    return best_individual

# Example usage
if __name__ == "__main__":
    garage_name = "south_campus"  # Example garage
    data: pd.DataFrame = load_data_from_mongodb(datetime.now())
    best_hyperparameters = genetic_algorithm(garage_name, data)
    print("Optimized hyperparameters:", best_hyperparameters)
