import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as patches
from matplotlib import cm

from overengineered_weight_calculator import VectorField, WeightCalculator


def plot_vector_field_and_projectiles_with_both_velocities(results):
    fig, ax = plt.subplots(figsize=(12, 12))
    ax.set_xlim(0, 800)
    ax.set_ylim(0, 400)
    ax.set_aspect('equal')
    ax.set_title("Vector field with Projectiles (Color Mapped by Weight)")
    ax.set_xlabel("x")
    ax.set_ylabel("y")

    # Normalize the weights for color mapping
    max_weight = max(results, key=lambda _x: _x[4])[4]
    min_weight = 0.0

    # Plot the vector field
    for x in range(0, 800, 50):
        for y in range(0, 400, 50):
            v_x, v_y = vector_field.compute_field(x, y)
            # Normalize arrow length for clarity
            norm = np.sqrt(v_x ** 2 + v_y ** 2)
            ax.arrow(x, y, v_x / norm * 30, v_y / norm * 30, head_width=10, head_length=10, fc='k', ec='k', alpha=0.4)

    # Plot the projectiles with arrows
    for x, y, velocity_x, velocity_y, weight in results:
        if weight >= 0.0:
            normalized_color = (weight - min_weight) / (max_weight - min_weight)
            ax.arrow(x, y, velocity_x * 3.0, velocity_y * 3.0, head_width=10, head_length=10,
                     fc=cm.viridis(normalized_color),
                     ec=cm.viridis(normalized_color))
            ax.add_patch(patches.Circle((x, y), 5, color=cm.viridis(normalized_color), alpha=0.6))

    # Add a color bar for better interpretation
    sm = plt.cm.ScalarMappable(cmap=cm.viridis, norm=plt.Normalize(vmin=min_weight, vmax=max_weight))
    sm.set_array([])
    plt.colorbar(sm, ax=ax, orientation='vertical', label='Weight')

    plt.show()


def sample_velocity_vectors():
    y_values = np.linspace(-3.0, 3.0, 9)
    sampled_velocities = []

    for v_y_ in y_values:
        if v_y_ == 3.0 or v_y_ == -3.0:
            v_x_ = 0
        else:
            v_x_ = -np.sqrt(3.0 ** 2 - v_y_ ** 2)
        sampled_velocities.append((v_x_, v_y_))

    return sampled_velocities


# Initialisation
test_points = [(x, y) for x in np.linspace(0, 801, 20) for y in range(0, 401, 50)]  # X est de 0 à -2.3
vector_field = VectorField(cannon_position=(20, 200), edge_point=(800, 200))
weight_calculator = WeightCalculator(vector_field)

# Compute weights for each test point
all_results_both_velocities = []

for x, y in test_points:
    velocities = sample_velocity_vectors()
    for v_x, v_y in velocities:
        weight = weight_calculator.compute_weight("Large", x, y, v_x, v_y)  # Changez "Small" à "Large"
        all_results_both_velocities.append((x, y, v_x, v_y, weight))

plot_vector_field_and_projectiles_with_both_velocities(all_results_both_velocities)
