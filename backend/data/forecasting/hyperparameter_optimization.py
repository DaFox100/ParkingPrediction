import random
import numpy as np
import pandas as pd
import sys
import matplotlib.pyplot as plt
import tensorflow as tf

from datetime import datetime
from pathlib import Path
from typing import List, Any, Dict
# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="keras.saving")

from data.forecasting.keras_model_file import build_model
from data.forecasting.long_term_model import train_long_model
from data.forecasting.data_functions import add_cyclical_time_encoding, add_event_impact_features,add_instruction_days, load_data_from_mongodb
from data.forecasting.constants import (
    GARAGE_NAMES,
    LONG_SEQ,
    LONG_FUTURE_STEPS,
    ENABLE_TIME_ENCODING,
    ENABLE_INSTR_DAY,
    ENABLE_EVENT_ENCODING
)

# Define the search space for hyperparameters
HYPERPARAMETER_SPACE = {
    "lstm_neurons_list": range(16, 320, 1),  # Range of numbers from 16 to 320 with a step of 1
    "lstm_layers": [1, 2, 3, 4],
    "dropout": (0.05, 0.9),  # Range for dropout values
    "learning_rate": (1e-4, 1e-2),  # Range for learning rate values
    "activation": ["leaky_relu", "gelu", "silu", "relu", "linear", "tanh", "hard_tanh", "celu", "elu", "mish", "sigmoid", "hard_sigmoid"],
    "optimizer": ["nadam", "adam", "adamw", "rmsprop", "lion", "adamax"],
    "batch_size": [64, 128, 256, 512]
}

starting_pops  = [
    {'lstm_neurons_list': [1024,1024,1024,1024],   'dropout': 0.55, 'learning_rate': 0.00075,'activation': "celu",      'optimizer': "adamw",   'batch_size': 128},
    # {'lstm_neurons_list': [32, 96],       'dropout': 0.35, 'learning_rate': 0.002,  'activation': 'sigmoid',     'optimizer': 'rmsprop', 'batch_size': 128},
    # {'lstm_neurons_list': [192, 32],      'dropout': 0.55, 'learning_rate': 0.002,  'activation': 'mish',        'optimizer': 'rmsprop', 'batch_size': 128},
    # {'lstm_neurons_list': [32, 64, 312],  'dropout': 0.35, 'learning_rate': 0.002,  'activation': 'hard_tanh',   'optimizer': 'rmsprop', 'batch_size': 64}
    ]
# Genetic algorithm parameters
POPULATION_SIZE = 36
GENERATIONS = 20
MUTATION_RATE = 0.2
ELITES_SIZE = 2

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
    val_loss = train_long_model(
        model=model,
        batch_size=individual["batch_size"],
        future_steps=LONG_FUTURE_STEPS,
        test_split=0.8,
        seq_size=LONG_SEQ,
        name=f"temp_model_{garage}",
        training_epochs=50,  # Use fewer epochs for faster evaluation
        data=data
    )
    return val_loss


def select_parents(population: List[Dict[str, Any]], fitness_scores: List[float]) -> List[Dict[str, Any]]:
    """Select individuals based on their fitness scores using tournament selection."""
    selected = []
    for _ in range(POPULATION_SIZE // 2):
        tournament = random.sample(list(zip(population, fitness_scores)), k=3)
        winner = min(tournament, key=lambda x: x[1])  # Select the individual with the lowest loss
        selected.append(winner[0])
    return selected


def crossover(parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Dict[str, Any]:
    """Perform intelligent crossover between two parents to produce an offspring."""
    offspring = {}
    for key in parent1.keys():
        if key == "lstm_neurons_list":
            # Intelligent crossover for lstm_neurons_list
            parent1_layers = parent1[key]
            parent2_layers = parent2[key]
            max_layers = max(len(parent1_layers), len(parent2_layers))

            offspring_layers = []
            for i in range(max_layers):
                if i < len(parent1_layers) and i < len(parent2_layers):
                    # Average the neuron counts for corresponding layers
                    avg_neurons = (parent1_layers[i] + parent2_layers[i]) // 2
                    offspring_layers.append(avg_neurons)
                elif i < len(parent1_layers):
                    offspring_layers.append(parent1_layers[i])
                elif i < len(parent2_layers):
                    offspring_layers.append(parent2_layers[i])

            offspring[key] = offspring_layers
        elif key == "lstm_layers":
            # Ensure lstm_layers is explicitly handled
            offspring[key] = random.choice([parent1[key], parent2[key]])
        else:
            # For other hyperparameters, randomly choose from one of the parents
            offspring[key] = random.choice([parent1[key], parent2[key]])
    return offspring


def mutate(individual: Dict[str, Any]) -> Dict[str, Any]:
    """Mutate an individual by randomly changing one of its hyperparameters."""
    if random.random() < MUTATION_RATE:
        key = random.choice(list(HYPERPARAMETER_SPACE.keys()))
        if key == "lstm_neurons_list":
            individual[key] = [random.choice(HYPERPARAMETER_SPACE[key]) for _ in range(random.randint(2, 4))]
        elif key == "dropout":
            individual[key] = random.uniform(*HYPERPARAMETER_SPACE[key])
        elif key == "learning_rate":
            individual[key] = random.uniform(*HYPERPARAMETER_SPACE[key])
        else:
            individual[key] = random.choice(HYPERPARAMETER_SPACE[key])
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
    """Run the genetic algorithm to optimize hyperparameters for a specific garage."""
    # Clear the best models file at the start of a new run
    with open("best_models.txt", "w") as f:
        f.write("Best Models per Generation\n")

    population = initialize_population()
    best_models = []  # To store the best model of each generation
    avg_val_losses = []  # To store the average validation loss of each generation
    lowest_val_losses = []  # To store the lowest validation loss of each generation
    elites = []  # To store the best-performing models across generations

    # Adaptive crossover rate based on fitness
    ADAPTIVE_CROSSOVER_RATE = 0.2

    for generation in range(GENERATIONS):
        print(f"Generation {generation + 1}")

        # Evaluate fitness for the population
        fitness_scores = [evaluate_fitness(ind, garage, data)[0] for ind in population]

        # Sort population by fitness
        sorted_population = sorted(zip(population, fitness_scores), key=lambda x: x[1])
        population = [ind for ind, _ in sorted_population]

        # Select parents
        parents = select_parents(population, fitness_scores)

        # Create the next generation
        next_generation = elites.copy()  # Start with elites
        while len(next_generation) < POPULATION_SIZE:
            parent1, parent2 = random.sample(parents, 2)

            # Adaptive crossover rate
            if random.random() < ADAPTIVE_CROSSOVER_RATE:
                offspring = crossover(parent1, parent2)
            else:
                offspring = random.choice([parent1, parent2])

            offspring = mutate(offspring)
            next_generation.append(offspring)

        # Add completely random individuals to maintain diversity
        num_random_individuals = POPULATION_SIZE // 5  # Add 10% of the population as random individuals
        for _ in range(num_random_individuals):
            layers = random.choice(HYPERPARAMETER_SPACE["lstm_layers"])
            neuron_layers = [random.choice(HYPERPARAMETER_SPACE["lstm_neurons_list"]) for _ in range(layers)]
            random_individual = {
                "lstm_neurons_list": neuron_layers,
                "dropout": random.choice(HYPERPARAMETER_SPACE["dropout"]),
                "learning_rate": random.choice(HYPERPARAMETER_SPACE["learning_rate"]),
                "activation": random.choice(HYPERPARAMETER_SPACE["activation"]),
                "optimizer": random.choice(HYPERPARAMETER_SPACE["optimizer"]),
                "batch_size": random.choice(HYPERPARAMETER_SPACE["batch_size"]),
                "lstm_layers": layers,
            }
            next_generation.append(random_individual)

        population = next_generation

        # Find the best models of the generation
        sorted_population = sorted(zip(population, fitness_scores), key=lambda x: x[1])
        elites = [ind for ind, _ in sorted_population[:ELITES_SIZE]]

        # Calculate and store average validation loss
        avg_val_loss = sum(fitness_scores) / len(fitness_scores)
        avg_val_losses.append(avg_val_loss)

        # Find the best model of the generation
        best_index = np.argmin(fitness_scores)
        best_model = population[best_index]
        best_loss = fitness_scores[best_index]
        best_models.append(best_model)

        # Store the lowest validation loss of the generation
        lowest_val_losses.append(best_loss)

        # Log the best model and its loss to a text file
        with open("best_models.txt", "a") as f:
            f.write(f"Generation {generation + 1}: {best_model}, Loss: {best_loss}\n")

        # Plot average and lowest validation loss per generation (updated every generation)
        plt.figure(figsize=(10, 6))
        plt.plot(range(1, len(avg_val_losses) + 1), avg_val_losses, marker="o", label="Average Loss")
        plt.plot(range(1, len(lowest_val_losses) + 1), lowest_val_losses, marker="x", label="Lowest Loss")
        plt.title("Validation Loss per Generation")
        plt.xlabel("Generation")
        plt.ylabel("Validation Loss")
        plt.legend()
        plt.grid(True)
        plt.savefig("validation_loss_per_generation.png")
        plt.close()

    # Return the best individual from the final generation
    fitness_scores = [evaluate_fitness(ind, garage, data)[0] for ind in population]
    best_individual = population[np.argmin(fitness_scores)]
    print("Best hyperparameters:", best_individual)
    return best_individual

# Example usage
if __name__ == "__main__":
    # Load your data here
    garage_name = "south"  # Example garage
    data: pd.DataFrame = load_data_from_mongodb(datetime.now())

    best_hyperparameters = genetic_algorithm(garage_name, data)
    print("Optimized hyperparameters:", best_hyperparameters)