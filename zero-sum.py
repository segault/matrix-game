#INPUT - Ulvi

from math import isfinite

EPSILON = 1e-9

def show_tableau(tableau):
    print("\nTableau:")
    for row in tableau:
        for col in row:
            print(f"{col:>8.2f}", end=" ")
        print()

def standardize(consts, coeffs):
    op = coeffs[-2].lower()
    coeffs.pop(-2)
    coeffs = [float(x) for x in coeffs]

    if op == "e":
        consts.append(coeffs); # <=
        consts.append([-x for x in coeffs]) # >= --> <=
    elif op == "ge":
        consts.append([-x for x in coeffs]) # >= --> <=
    else:
        consts.append(coeffs)

def get_input():
    global decisions
    global is_maximization
    is_maximization = input("Is this a maximization problem? (y/n): ").strip().lower() == 'y'
    decisions = int(input("Enter the number of decision variables: "))
    count = int(input("Enter the number of constraints: "))
    constraints = []
    objective = list(map(float, input("Enter the coefficients and constant (if applicable) \
of the objective function (space-separated):\nO: ").split()))

    # standardize objective
    # moving all terms to the left (given like C = 3x + 3y) negates them
    # but then if minimizing, we negate again to make it a max,
    # therefore only the max really gets negated
    # if is_maximization is True:
    #     objective = [-x for x in objective]
    # else:
    #     if len(objective) > decisions:
    #         objective[-1] *= -1 # if there's a constant, it's negated. why?
    #
    if len(objective) == decisions + 1:
        constant = objective.pop()
        if not is_maximization:
            constant *= -1 # if there's a constant, it's negated. why?
    else:
        constant = 0.0

    if is_maximization is True:
        objective = [-x for x in objective]

    print("Enter constraints, relation (e/ge/le), and RHS (space separated)\n \
e = equals | ge = greater than/equals | le = less than/equals: ")
    for i in range(count):
        coeffs = list(map(str, input(f"{i+1}: ").split()))
        standardize(constraints, coeffs)

    tableau = []
    m = len(constraints)

    for i in range(m):
        constraint = constraints[i]

        slack = [0] * m
        slack[i] = 1

        row = constraint[:-1] + slack + [constraint[-1]]
        tableau.append(row)

    tableau.append(objective + [0] * m + [constant])

    return tableau


def check_negative(tableau):
    for i in range(len(tableau[0])-1):
        if tableau[-1][i] < -EPSILON:
            return True
    return False

def phaseI(tableau, basis=None):
    ratios = []
    col = None
    for i in range(len(tableau[0])-1):
        if tableau[-1][i] < -EPSILON: #leftmost first
            col = i
            break

    if col is None:
        return tableau

    #compare ratios
    for j in range(len(tableau)-1):
        if tableau[j][col] > EPSILON:
            ratio = tableau[j][-1]/tableau[j][col]
            ratios.append((ratio, j))

    if not ratios:
        raise ValueError("PHASE I: No valid ratios found. The problem is unbounded.")

    #lowest ratio
    if basis is None:
        lowest, row = min(ratios)
    else:
        # Bland tie-breaker: choose the smallest-index basic variable.
        # This avoids cycling when a game has multiple optimal strategies.
        lowest = min(ratio for ratio, _ in ratios)
        row = min(
            (basis[r], r) for ratio, r in ratios
            if ratio <= lowest + EPSILON
        )[1]

    #pivot
    pivot = tableau[row][col]
    for x in range(len(tableau[0])):
        tableau[row][x] /= pivot

    for y in range(len(tableau)):
        if y == row:
            continue

        else:
            factor = tableau[y][col]

            tableau[y] = [
                    tableau[y][x] - factor * tableau[row][x]
                    for x in range(len(tableau[0]))
            ]

    if basis is not None:
        basis[row] = col
    return tableau

def check_dual(tableau):
    for i in range(len(tableau)-1):
        if tableau[i][-1] < -EPSILON:
            return True
    return False

def phaseII(tableau):
    ratios = []
    row = None

    for i in range(len(tableau) - 1):
        if tableau[i][-1] < -EPSILON:
            if row is None or tableau[i][-1] < tableau[row][-1]:
                row = i

    if row is None:
        return tableau

    #compare ratios again
    for j in range(len(tableau[0]) - 1):
        if tableau[row][j] < -EPSILON:
            ratio = tableau[-1][j] / -tableau[row][j]
            ratios.append((ratio, j))

    if not ratios:
        raise ValueError("PHASE II: No valid ratios found. The problem is infeasible.")

    #lowest ratio
    lowest, col = min(ratios)

    #pivot
    pivot = tableau[row][col]
    tableau[row] = [x / pivot for x in tableau[row]]

    for y in range(len(tableau)):
        if y == row:
            continue

        factor = tableau[y][col]

        tableau[y] = [
            tableau[y][x] - factor * tableau[row][x]
            for x in range(len(tableau[0]))
        ]

    return tableau

def extract_soln(tableau):
    global is_maximization
    global decisions
    solution = [0.0] * decisions
    eps = EPSILON

    for col in range(decisions):
        for row in range(len(tableau) - 1):
            if (
                abs(tableau[row][col] - 1) < eps
                and all(
                    abs(tableau[k][col]) < eps
                    for k in range(len(tableau) - 1)
                    if k != row
                )
                and abs(tableau[-1][col]) < eps
            ):
                solution[col] = tableau[row][-1]
                break

    optimum = tableau[-1][-1]
    if not is_maximization:
        optimum = -optimum
    return tuple(solution), optimum


# MATRIX GAME - two-player zero-sum games (2 to 10 strategies per player)

def prepare_payoff_matrix(payoffs):
    """Shift ALL payoffs by the same constant so every entry is > 0."""
    smallest = min(min(row) for row in payoffs)
    shift = 1.0 - smallest if smallest <= 0 else 0.0
    adjusted = [[value + shift for value in row] for row in payoffs]
    return adjusted, shift


def solve_matrix_game(payoffs):
    """Return both players' optimal strategies and the ORIGINAL game value.

    Player A chooses a row and maximizes its payoff; player B chooses a
    column and minimizes A's payoff. The game is two-player and zero-sum.

    For positive adjusted matrix M, solve via the EXISTING simplex pivot:
        maximize sum(y_j)
        subject to M*y <= 1, y >= 0

    The solution y yields player B's strategy. The dual variables, stored
    in the final objective row at the slack columns, yield player A's.
    """
    rows = len(payoffs)
    if not 2 <= rows <= 10:
        raise ValueError("The payoff matrix must have 2 to 10 rows.")
    cols = len(payoffs[0])
    if not 2 <= cols <= 10:
        raise ValueError("The payoff matrix must have 2 to 10 columns.")
    if any(len(row) != cols for row in payoffs):
        raise ValueError("All rows must have the same number of columns.")
    if any(not isfinite(value) for row in payoffs for value in row):
        raise ValueError("All payoffs must be finite numbers.")

    adjusted, shift = prepare_payoff_matrix(payoffs)

    # A slack variable for each ROW constraint. The final row holds the
    # negative objective coefficients, just like the original simplex code.
    tableau = []
    for i, row in enumerate(adjusted):
        slack = [0.0] * rows
        slack[i] = 1.0
        tableau.append(row[:] + slack + [1.0])
    tableau.append([-1.0] * cols + [0.0] * rows + [0.0])

    # Track which variable is basic in each constraint row.
    # Initially these are all slack variables.
    basis = [cols + i for i in range(rows)]
    iterations = 0
    while check_negative(tableau):
        phaseI(tableau, basis)
        iterations += 1
        if iterations > 10000:
            raise ArithmeticError("Simplex reached its iteration limit.")

    scale = tableau[-1][-1]  # optimal sum(y) = 1 / adjusted game value
    if scale <= EPSILON:
        raise ArithmeticError("Could not compute a valid game value.")

    # Player B: original decision variables, recovered using the basis.
    y = [0.0] * cols
    for r, variable in enumerate(basis):
        if variable < cols:
            y[variable] = tableau[r][-1]

    # Player A: optimal dual variables (shadow prices of row constraints).
    x = [tableau[-1][cols + i] for i in range(rows)]

    def probabilities(values):
        cleaned = [0.0 if abs(v) < EPSILON else v / scale for v in values]
        if any(v < -1e-7 for v in cleaned):
            raise ArithmeticError("A negative strategy probability was found.")
        cleaned = [v if v > 0 else 0.0 for v in cleaned]
        total = sum(cleaned)
        if abs(total - 1) > 1e-6:
            raise ArithmeticError("Strategy probabilities do not sum to 1.")
        return [v / total for v in cleaned]

    player_a = probabilities(x)
    player_b = probabilities(y)
    adjusted_value = 1.0 / scale
    original_value = adjusted_value - shift

    return {
        "player_a": player_a,
        "player_b": player_b,
        "game_value": original_value,
        "adjusted_value": adjusted_value,
        "shift": shift,
        "adjusted_matrix": adjusted,
    }


def read_dimension(label):
    while True:
        try:
            number = int(input(f"{label} (2-10): "))
            if 2 <= number <= 10:
                return number
        except ValueError:
            pass
        print("Please enter a whole number from 2 to 10.")


def matrix_game_input():
    print("\nTwo-player zero-sum matrix game")
    print("Player A chooses a row; player B chooses a column.")
    rows = read_dimension("Number of rows")
    cols = read_dimension("Number of columns")
    matrix = []
    print(f"Enter {rows} rows of {cols} payoffs, separated by spaces:")
    for i in range(rows):
        while True:
            try:
                values = [float(x) for x in input(f"Row {i+1}: ").split()]
                if len(values) != cols or not all(isfinite(v) for v in values):
                    raise ValueError
                matrix.append(values)
                break
            except ValueError:
                print(f"Enter exactly {cols} finite numbers separated by spaces.")
    return matrix


def run_matrix_game():
    payoffs = matrix_game_input()
    result = solve_matrix_game(payoffs)
    print("\nOriginal payoff matrix:")
    for row in payoffs:
        print("  ", " ".join(f"{v:9.3f}" for v in row))

    if result["shift"]:
        print(f"\nAdded {result['shift']:.6g} to EVERY payoff before simplex:")
        for row in result["adjusted_matrix"]:
            print("  ", " ".join(f"{v:9.3f}" for v in row))
    else:
        print("\nNo payoff adjustment needed (all entries already positive).")

    print("\nOptimal strategy for Player A (rows):")
    for i, probability in enumerate(result["player_a"], start=1):
        print(f"  Row {i}: {probability:.6f} ({probability:.2%})")

    print("Optimal strategy for Player B (columns):")
    for j, probability in enumerate(result["player_b"], start=1):
        print(f"  Column {j}: {probability:.6f} ({probability:.2%})")

    print(f"\nAdjusted game value: {result['adjusted_value']:.6f}")
    print(f"Original game value: {result['adjusted_value']:.6f} "
          f"- {result['shift']:.6f} = {result['game_value']:.6f}")


def run_linear_program():
    """Retain the original linear-program mode."""
    tableau = get_input()
    show_tableau(tableau)

    rhs_feasible = all(row[-1] >= 0 for row in tableau[:-1])
    dual_feasible = all(x >= 0 for x in tableau[-1][:-1])

    if rhs_feasible:
        while check_negative(tableau):
            phaseI(tableau)
    elif dual_feasible:
        while check_dual(tableau):
            phaseII(tableau)
    else:
        while check_negative(tableau):
            phaseI(tableau)
        while check_dual(tableau):
            phaseII(tableau)

    coords, optm = extract_soln(tableau)
    print(f"\nOptimal solution found: {optm:.2f} at ")
    for value in coords:
        print(f"{value:.2f}")


if __name__ == "__main__":
    print("1. Linear programming (original simplex)")
    print("2. Two-player zero-sum matrix game")
    choice = input("Choose 1 or 2: ").strip()
    try:
        if choice == "1":
            run_linear_program()
        elif choice == "2":
            run_matrix_game()
        else:
            print("Invalid choice. Enter 1 or 2.")
    except (ValueError, ArithmeticError) as exc:
        print(f"Error: {exc}")
