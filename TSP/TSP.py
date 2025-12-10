import random
import math
import matplotlib.pyplot as plt

# 도시 생성 및 거리 계산
def generate_cities(n_cities, width=200, height=200):
    cities = []
    for _ in range(n_cities):
        x = random.uniform(0, width)
        y = random.uniform(0, height)
        cities.append((x, y))
    return cities

def euclidean_distance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def path_distance(route, cities):
    distance = 0.0
    num_cities = len(route)
    for i in range(num_cities):
        city_a = cities[route[i]]
        city_b = cities[route[(i + 1) % num_cities]]
        distance += euclidean_distance(city_a, city_b)
    return distance

def fitness(route, cities):
    d = path_distance(route, cities)
    return 1.0 / d if d > 0 else float("inf")


# 초기 개체군 생성
def create_initial_population(pop_size, n_cities):
    population = []
    base = list(range(n_cities))
    for _ in range(pop_size):
        route = base[:]
        random.shuffle(route)
        population.append(route)
    return population


# 선택 (Tournament Selection)
def tournament_selection(population, cities, k=3):
    competitors = random.sample(population, k)
    competitors_fitness = [(fitness(r, cities), r) for r in competitors]
    competitors_fitness.sort(key=lambda x: x[0], reverse=True)
    return competitors_fitness[0][1][:]


# 교차 (Ordered Crossover)
def ordered_crossover(parent1, parent2):
    size = len(parent1)
    child = [None] * size
    start, end = sorted(random.sample(range(size), 2))

    for i in range(start, end + 1):
        child[i] = parent1[i]

    p2_idx = 0
    for i in range(size):
        if child[i] is None:
            while parent2[p2_idx] in child:
                p2_idx += 1
            child[i] = parent2[p2_idx]
            p2_idx += 1

    return child


# 돌연변이 (Swap Mutation)
def swap_mutation(route, mutation_rate):
    for i in range(len(route)):
        if random.random() < mutation_rate:
            j = random.randint(0, len(route) - 1)
            route[i], route[j] = route[j], route[i]


# 유전자 알고리즘 루프
def genetic_algorithm(cities,
                      pop_size=100,
                      generations=500,
                      mutation_rate=0.02,
                      tournament_k=3):

    n_cities = len(cities)
    population = create_initial_population(pop_size, n_cities)

    best_route = None
    best_distance = float("inf")
    best_distances_per_gen = []

    for gen in range(generations):
        fitness_values = [fitness(route, cities) for route in population]
        distances = [1.0 / f for f in fitness_values]

        min_idx = distances.index(min(distances))
        current_best_route = population[min_idx]
        current_best_distance = distances[min_idx]

        if current_best_distance < best_distance:
            best_distance = current_best_distance
            best_route = current_best_route[:]

        best_distances_per_gen.append(best_distance)

        new_population = []
        while len(new_population) < pop_size:
            parent1 = tournament_selection(population, cities, k=tournament_k)
            parent2 = tournament_selection(population, cities, k=tournament_k)
            child = ordered_crossover(parent1, parent2)
            swap_mutation(child, mutation_rate)
            new_population.append(child)

        population = new_population

    return best_route, best_distance, best_distances_per_gen


# 시각화
def plot_route(best_route, cities, title="최적 경로 (Best Route Found)"):
    xs = [cities[i][0] for i in best_route]
    ys = [cities[i][1] for i in best_route]
    xs.append(cities[best_route[0]][0])
    ys.append(cities[best_route[0]][1])
    plt.plot(xs, ys, marker='o')
    plt.title(title)
    plt.xlabel("X")
    plt.ylabel("Y")

def plot_distance_progress(distances, title="세대별 최단 거리 (Distance over Generations)"):
    plt.plot(range(len(distances)), distances)
    plt.title(title)
    plt.xlabel("세대 (Generation)")
    plt.ylabel("거리 (Distance)")


# main
def main():

    n_cities = 20
    pop_size = 100
    generations = 500
    mutation_rate = 0.02
    tournament_k = 3

    cities = generate_cities(n_cities)

    best_route, best_distance, best_distances_per_gen = genetic_algorithm(
        cities,
        pop_size=pop_size,
        generations=generations,
        mutation_rate=mutation_rate,
        tournament_k=tournament_k
    )

    print("최적 경로 길이:", best_distance)
    print("최적 경로:", best_route)

    plt.figure(figsize=(12, 4))

    plt.subplot(1, 2, 1)
    plot_route(best_route, cities)

    plt.subplot(1, 2, 2)
    plot_distance_progress(best_distances_per_gen)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
