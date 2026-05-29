import time
import sys
import json

with open("profiles.json", "r") as f:
    wrestlers = json.load(f)

def odds(a, b):
    elo_diff = abs(a['Elo'] - b['Elo'])
    odds = 1 / (1 + 10 ** (elo_diff / 400))
    return odds

def calculate_elo(athlete):
    wins = athlete['Wins']
    losses = athlete['Losses']

    athlete['Elo'] = athlete['Elo'] + wins - losses

def predict(name1, name2):
    try:
        athlete1 = wrestlers[name1]
        athlete2 = wrestlers[name2]

        p1 = odds(athlete1, athlete2)

        print(f'\n{name1} has a {p1 * 100:.1f}% chance to beat {name2}')
        print(f'{name2} has a {(1 - p1) * 100:.1f}% chance to beat {name1}')

    except Exception as e:
        print(e)


def take_inputs():
    a = input("Wrestler 1: ").lower().strip()
    while a not in wrestlers:
        print("Not a wrestler")
        a = input("Wrestler 1: ").lower().strip()

    b = input("Wrestler 2: ").lower().strip()
    while b not in wrestlers:
        print("Not a wrestler")
        b = input("Wrestler 2: ").lower().strip()

    predict(a, b)
