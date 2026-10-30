def get_input():
    matrix = []
    n, m = tuple(map(int, input("What are the dimensions (n, m): ").split(',')))
    for i in range(n):
        while len(row := list(map(float, input(f"row {i+1}: ").split()))) != m:
            print("Enter m entries for each row")

        matrix.append(row)

    return matrix

print(get_input())
