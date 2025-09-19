import random
import numpy as np
import pandas as pd
import sys
import matplotlib.pyplot as plt
import tensorflow as tf
import gc
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Any, Dict

# Suppress TensorFlow logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="keras.saving")

from data.forecasting.keras_model_file import build_model
from data.forecasting.long_term_model import train_long_model_with_generator
from data.forecasting.data_functions import add_cyclical_time_encoding, add_event_impact_features,add_instruction_days, load_data_from_mongodb
from data.forecasting.constants import (
    GARAGE_NAMES,
    LONG_SEQ,
    LONG_FUTURE_STEPS,
    ENABLE_TIME_ENCODING,
    ENABLE_INSTR_DAY,
    ENABLE_EVENT_ENCODING
)

# Update the search space for hyperparameters
HYPERPARAMETER_SPACE = {
    "lstm_neurons_list": range(16, 512, 1),
    "lstm_layers": [1, 2, 3, 4, 5],
    "dropout": (0.05, 0.9),
    "learning_rate": (1e-4, 5e-3),
    "activation": ["tanh", "hard_tanh", "celu", "elu", "sigmoid", "hard_sigmoid"],
    "optimizer": ["nadam", "adam", "rmsprop", "lion", "adamax"],
    "batch_size": [256, 512, 1024]
}

starting_pops = [
    # # South
    # {'lstm_neurons_list': [77, 73, 205, 216], 'lstm_layers': 4, 'dropout': 0.2500845427465502, 'learning_rate': 0.0018339163857906118, 'activation': 'tanh', 'optimizer': 'adamax', 'batch_size': 512, 'Loss': 0.00402255542576133},
    # {'lstm_neurons_list': [114, 170, 429, 412], 'lstm_layers': 4, 'dropout': 0.39671304557770519, 'learning_rate': 0.0033710608358507514, 'activation': 'sigmoid', 'optimizer': 'rmsprop', 'batch_size': 1024, 'Loss': 0.004722285505342086},
    # # West
    # {'lstm_neurons_list': [110, 183, 207, 508], 'lstm_layers': 4, 'dropout': 0.44826529785781433, 'learning_rate': 0.0004833113226494442, 'activation': 'sigmoid', 'optimizer': 'adam', 'batch_size': 256, 'Loss': 0.001618490084335208},
    # {'lstm_neurons_list': [112, 232, 229, 471], 'lstm_layers': 4, 'dropout': 0.40284652978581433, 'learning_rate': 0.0005810818127695974, 'activation': 'sigmoid', 'optimizer': 'lion', 'batch_size': 256, 'Loss': 0.0017113440755973635},
    # # South Campus
    # {'lstm_neurons_list': [141, 258, 327, 245, 275], 'lstm_layers': 5, 'dropout': 0.15608111088723042, 'learning_rate': 0.000649410048921348, 'activation': 'gelu', 'optimizer': 'rmsprop', 'batch_size': 256, 'Loss': 0.006575405358216176},
    # {'lstm_neurons_list': [180, 104, 508, 253], 'lstm_layers': 4, 'dropout': 0.3651523846670196, 'learning_rate': 0.002592602448410859, 'activation': 'leaky_relu', 'optimizer': 'rmsprop', 'batch_size': 256, 'Loss': 0.006179669469593977},
    # {'lstm_neurons_list': [112, 232, 346, 443], 'lstm_layers': 4, 'dropout': 0.40284652978581433, 'learning_rate': 0.001867326325308185, 'activation': 'leaky_relu', 'optimizer': 'rmsprop', 'batch_size': 256, 'Loss': 0.00690326185325325},
    # {'lstm_neurons_list': [110, 180, 508, 253], 'lstm_layers': 4, 'dropout': 0.3651523846670196, 'learning_rate': 0.002592602448410859, 'activation': 'celu', 'optimizer': 'adamw', 'batch_size': 1024, 'Loss': 0.00729},
    # # North
    # {'lstm_neurons_list': [423, 176, 436, 325], 'lstm_layers': 4, 'dropout': 0.5745106585317661, 'learning_rate': 0.001605169386433909, 'activation': 'sigmoid', 'optimizer': 'adam', 'batch_size': 256, 'Loss': 0.0002168411923235003},
    # {'lstm_neurons_list': [424, 210, 324, 431], 'lstm_layers': 4, 'dropout': 0.5745106585317661, 'learning_rate': 0.001605169386433909, 'activation': 'sigmoid', 'optimizer': 'adam', 'batch_size': 256, 'Loss': 0.00020756182103530536},
    # {'lstm_neurons_list': [327, 179, 417, 317], 'lstm_layers': 4, 'dropout': 0.5745106585317661, 'learning_rate': 0.0009967926629038712, 'activation': 'sigmoid', 'optimizer': 'adamw', 'batch_size': 256, 'Loss': 0.0018771779723465443}
]

# Genetic algorithm parameters
POPULATION_SIZE = 4
GENERATIONS = 50
MUTATION_RATE = 0.8
ELITES_SIZE = 1

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


def evaluate_fitness(individual: Dict[str, Any], garage: str, data: np.ndarray) -> float:
    """Evaluate the fitness of an individual by training a model and returning the validation loss."""
    # Ensure lstm_neurons_list is always a list
    if isinstance(individual["lstm_neurons_list"], int):
        individual["lstm_neurons_list"] = [individual["lstm_neurons_list"]]

    print(f"Evaluating model for garage: {garage}")
    print("Hyperparameters:")
    for key, value in individual.items():
        print(f"  {key}: {value}")

    # Select optimizer
    if   individual["optimizer"] == "adam":
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

    model = build_model(
        lstm_neurons_list=individual["lstm_neurons_list"],
        dropout=individual["dropout"],
        seq_size=LONG_SEQ,
        activation=individual["activation"],
        n_feature= 4 + EXTRA_LONG_DATA,
        future_steps=LONG_FUTURE_STEPS,
        garage_no=GARAGE_NAMES.index(garage),
        optimizer=optimizer
    )

    # Train the model and get the validation loss
    val_loss = train_long_model_with_generator(
        model=model,
        batch_size=individual["batch_size"],
        future_steps=LONG_FUTURE_STEPS,
        test_split=0.98,
        seq_size=LONG_SEQ,
        name=f"temp_model_{garage}",
        training_epochs=25,
        data=data
    )

    # Clear session and collect garbage
    tf.keras.backend.clear_session()
    del model, optimizer
    gc.collect()
    return val_loss


# Select parents using tournament selection
def select_parents(population: List[Dict[str, Any]], fitness_scores: List[float]) -> List[Dict[str, Any]]:
    """Select individuals based on their fitness scores using tournament selection."""
    selected = []
    for _ in range(POPULATION_SIZE // 2):
        tournament = random.sample(list(zip(population, fitness_scores)), k=4)
        winner = min(tournament, key=lambda x: x[1])  # Select the individual with the lowest loss
        selected.append(winner[0])
    return selected


# Perform intelligent crossover between two parents
def crossover(parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Dict[str, Any]:
    """Perform intelligent crossover between two parents to produce an offspring (average neurons, clamp to bounds)."""
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
    """Mutate an individual by randomly changing one of its hyperparameters (mutation rate controls change size)."""
    if random.random() < mutation_rate:
        key = random.choice(list(HYPERPARAMETER_SPACE.keys()))
        if key == "lstm_neurons_list":
            min_n, max_n = min(HYPERPARAMETER_SPACE["lstm_neurons_list"]), max(HYPERPARAMETER_SPACE["lstm_neurons_list"])
            new_layers = []
            for n in individual[key]:
                # Change by +/- (10% to 50%) depending on mutation rate
                max_change = 0.1 + 0.4 * mutation_rate
                delta = int(n * random.uniform(-max_change, max_change))
                new_n = max(min_n, min(max_n, n + delta))
                new_layers.append(new_n)
            individual[key] = new_layers
            individual["lstm_layers"] = len(new_layers)
        elif key == "dropout":
            val = individual[key]
            min_d, max_d = HYPERPARAMETER_SPACE["dropout"]
            max_change = 0.1 + 0.4 * mutation_rate
            delta = val * random.uniform(-max_change, max_change)
            new_val = max(min_d, min(max_d, val + delta))
            individual[key] = new_val
        elif key == "learning_rate":
            val = individual[key]
            min_lr, max_lr = HYPERPARAMETER_SPACE["learning_rate"]
            max_change = 0.1 + 0.4 * mutation_rate
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


def calculate_diversity(population: List[Dict[str, Any]]) -> float:
    """Calculate diversity of the population based on hyperparameter differences."""
    diversity = 0
    for i, ind1 in enumerate(population):
        for j, ind2 in enumerate(population):
            if i < j:
                diversity += sum(1 for key in ind1 if ind1[key] != ind2[key])
    return diversity / (len(population) * (len(population) - 1) / 2)

def genetic_algorithm(garage: str, data: np.ndarray):
    """Run the genetic algorithm to optimize hyperparameters for a specific garage and save population hyperparameters for each generation."""

    # Clear the best models file at the start of a new run
    with open(f"{garage}_best_models.txt", "w") as f:
        f.write("Best Models per Generation\n")

    population = initialize_population()
    best_models = []  # To store the best model of each generation
    avg_val_losses = []  # To store the average validation loss of each generation
    lowest_val_losses = []  # To store the lowest validation loss of each generation
    elites = []  # To store the best-performing models across all generations
    elite_losses = []  # Store their losses

    # Adaptive crossover rate based on fitness
    ADAPTIVE_CROSSOVER_RATE = 0.7

    initial_mutation_rate = 0.8
    final_mutation_rate = 0.1
    mutation_decay = (initial_mutation_rate - final_mutation_rate) / GENERATIONS

    for generation in range(GENERATIONS):
        print(f"Generation {generation + 1}")
        # Simulated annealing: decrease mutation rate over time
        mutation_rate = max(final_mutation_rate, initial_mutation_rate - mutation_decay * generation)

        # Evaluate fitness for the population serially
        fitness_scores = [evaluate_fitness(ind, garage, data)[0] for ind in population]

        # Sort population by fitness
        sorted_population_scores = sorted(zip(population, fitness_scores), key=lambda x: x[1])
        population = [ind for ind, score in sorted_population_scores]
        fitness_scores = [score for ind, score in sorted_population_scores]

        # Update elites: keep only the best ELITES_SIZE models ever seen
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

        # Select parents (include current elites)
        selected_parents = select_parents(population, fitness_scores) + elites

        next_generation = []
        # Add completely random individuals to maintain diversity
        num_random_individuals = POPULATION_SIZE // 5  # Add a percent of the population as random individuals
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
        with open(f"{garage}_best_models.txt", "a") as f:
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
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2)

        # Plot average and lowest validation loss per generation (updated every generation)
        plt.figure(figsize=(12, 6))
        plt.plot(range(1, len(avg_val_losses) + 1), avg_val_losses, marker="o", label="Average Loss")
        plt.plot(range(1, len(lowest_val_losses) + 1), lowest_val_losses, marker="x", label="Lowest Loss")
        plt.title("Validation Loss per Generation")
        plt.xlabel("Generation")
        plt.ylabel("Validation Loss")
        plt.legend()
        plt.grid(True)
        plt.savefig(f"{garage}_validation_loss_per_generation.png")
        plt.close()

        # Clear TensorFlow session and collect garbage to prevent memory leaks
        tf.keras.backend.clear_session()
        gc.collect()

    # Return the best individual from the final generation
    # Now, best individual is the best elite
    best_elite_idx = elite_losses.index(min(elite_losses))
    best_individual = elites[best_elite_idx]
    print("Best hyperparameters:", best_individual)
    return best_individual

# Example usage
if __name__ == "__main__":
    garage_name = "south"  # Example garage
    data: pd.DataFrame = load_data_from_mongodb(datetime.now())

    best_hyperparameters = genetic_algorithm(garage_name, data)
    print("Optimized hyperparameters:", best_hyperparameters)
