def get_input():
    matrix = []
    dim = int(input("What are the dimensions (nxn): "))
    for i in range(dim):
        row = list(map(str, input(f"row {i+1}: ").split()))

    return matrix
