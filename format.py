import csv
import json
import os
import re

WEIGHT_CLASSES = [106, 113, 120, 126, 132, 138, 144, 150, 157, 165, 175, 190, 215, 285]

class WrestlingDatabase:
    def __init__(self, json_path='profiles.json', default_elo=1200, k_factor=32):
        self.json_path = json_path
        self.default_elo = default_elo
        self.k_factor = k_factor
        self.profiles = self.load_profiles()
        self.match_log_lines = []

    def load_profiles(self):
        if os.path.exists(self.json_path) and os.path.getsize(self.json_path) > 0:
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def save_profiles(self):
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(self.profiles, f, indent=4)

    def ensure_athlete(self, name, team, weight):
        if name not in self.profiles:
            self.profiles[name] = {
                "name": name,
                "team": team,
                "current_weight": weight,
                "elo": self.default_elo,
                "wins": 0,
                "losses": 0,
                "pins": 0,
                "tech_falls": 0,
                "major_decisions": 0,
                "decisions": 0
            }
        else:
            if weight:
                self.profiles[name]["current_weight"] = weight

    def process_match(self, winner, w_team, loser, l_team, weight, win_type):
        self.ensure_athlete(winner, w_team, weight)
        self.ensure_athlete(loser, l_team, weight)

        old_elo_w = self.profiles[winner]["elo"]
        old_elo_l = self.profiles[loser]["elo"]

        self.profiles[winner]["wins"] += 1
        self.profiles[loser]["losses"] += 1

        wt_upper = win_type.upper()
        if "F" in wt_upper or "FALL" in wt_upper:
            self.profiles[winner]["pins"] += 1
        elif "TF" in wt_upper or "TECH" in wt_upper:
            self.profiles[winner]["tech_falls"] += 1
        elif "MD" in wt_upper or "MAJOR" in wt_upper:
            self.profiles[winner]["major_decisions"] += 1
        else:
            self.profiles[winner]["decisions"] += 1

        exp_w = 1 / (1 + 10 ** ((old_elo_l - old_elo_w) / 400))
        exp_l = 1 / (1 + 10 ** ((old_elo_w - old_elo_l) / 400))

        new_elo_w = round(old_elo_w + self.k_factor * (1.0 - exp_w))
        new_elo_l = round(old_elo_l + self.k_factor * (0.0 - exp_l))

        self.profiles[winner]["elo"] = new_elo_w
        self.profiles[loser]["elo"] = new_elo_l

        log_line = f"{winner} ({old_elo_w}) beat {loser} ({old_elo_l}) -> New: {new_elo_w}/{new_elo_l}"
        self.match_log_lines.append(log_line)

    def save_full_log(self, output_txt='full_log.txt'):
        with open(output_txt, 'a', encoding='utf-8') as f:
            f.write("\n" + "\n".join(self.match_log_lines))

    def generate_athlete_json(self, output_json='athlete_data.json'):
        if not self.profiles:
            return

        athlete_reference = {}
        for name in sorted(self.profiles.keys()):
            athlete_reference[name] = {
                "weight_class": self.profiles[name].get('current_weight', 'Unknown'),
                "team": self.profiles[name].get('team', 'Unknown Team')
            }
        
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(athlete_reference, f, indent=4)

    def predict_match(self, wrestler_a, wrestler_b, penalty_per_class=45):
        if wrestler_a not in self.profiles or wrestler_b not in self.profiles:
            return "One or both wrestlers not found in database profiles."

        prof_a = self.profiles[wrestler_a]
        prof_b = self.profiles[wrestler_b]

        elo_a = prof_a["elo"]
        elo_b = prof_b["elo"]

        def get_weight_idx(w_str):
            try:
                num = int(re.sub(r'\D', '', str(w_str)))
                return WEIGHT_CLASSES.index(num) if num in WEIGHT_CLASSES else 0
            except ValueError:
                return 0

        idx_a = get_weight_idx(prof_a["current_weight"])
        idx_b = get_weight_idx(prof_b["current_weight"])

        class_diff = idx_a - idx_b
        adjusted_elo_a = elo_a + (class_diff * penalty_per_class)
        
        prob_a = 1 / (1 + 10 ** ((elo_b - adjusted_elo_a) / 400))
        prob_b = 1 - prob_a

        print(f"\nMatch Prediction: {wrestler_a} vs {wrestler_b}")
        print(f"   {wrestler_a} (Base ELO: {elo_a}, Weight: {prof_a['current_weight']} lbs)")
        print(f"   {wrestler_b} (Base ELO: {elo_b}, Weight: {prof_b['current_weight']} lbs)")
        print(f"   Weight disparity adjustment shifts line by: {class_diff * penalty_per_class} points.")
        print(f"   Win Expectancy -> {wrestler_a}: {prob_a:.1%} | {wrestler_b}: {prob_b:.1%}")

    def show_top_pfp(self):
        if not self.profiles:
            print("No athlete data available.")
            return
        sorted_pfp = sorted(self.profiles.values(), key=lambda x: x['elo'], reverse=True)[:10]
        print("\n==============================================")
        print("             TOP 10 POUND-FOR-POUND           ")
        print("==============================================")
        for rank, athlete in enumerate(sorted_pfp, 1):
            print(f"{rank:02d}. {athlete['name']:<22} | ELO: {athlete['elo']:<5} | Weight: {athlete['current_weight']:<4} | Team: {athlete['team']}")
        print("==============================================")

    def show_top_weight_class(self, target_weight, limit):
        if not self.profiles:
            print("No athlete data available.")
            return
        filtered = [a for a in self.profiles.values() if str(a.get('current_weight', '')).strip() == str(target_weight).strip()]
        if not filtered:
            print(f"No wrestlers found currently competing in the {target_weight} lb weight class.")
            return
        sorted_weight = sorted(filtered, key=lambda x: x['elo'], reverse=True)[:limit]
        print(f"\n==============================================")
        print(f"         TOP {limit} RANKINGS FOR {target_weight} LBS     ")
        print(f"==============================================")
        for rank, athlete in enumerate(sorted_weight, 1):
            print(f"{rank:02d}. {athlete['name']:<22} | ELO: {athlete['elo']:<5} | Team: {athlete['team']}")
        print("==============================================")


def clean_cell(value):
    return re.sub(r'^="|"$', '', value).strip()

def ingest_csv(file_path):
    db = WrestlingDatabase()
    
    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = [clean_cell(col) for col in next(reader)]
        
        w_idx = header.index("Winning Wrestler")
        w_team_idx = header.index("Winning Team")
        l_idx = header.index("Losing Wrestler")
        l_team_idx = header.index("Losing Team")
        weight_idx = header.index("Weight")
        type_idx = header.index("Win Type")

        for row in reader:
            if not row:
                continue
                
            win_type = clean_cell(row[type_idx])
            if win_type.upper() == "BYE":
                continue

            winner = clean_cell(row[w_idx])
            w_team = clean_cell(row[w_team_idx])
            loser = clean_cell(row[l_idx])
            l_team = clean_cell(row[l_team_idx])
            weight = clean_cell(row[weight_idx])

            if winner and loser:
                db.process_match(winner, w_team, loser, l_team, weight, win_type)

    db.save_profiles()
    return db


if __name__ == "__main__":
    input("Press Enter to initialize database and parse battle_log.csv...")
    
    wrestling_db = ingest_csv('battle_log.csv')
    wrestling_db.generate_athlete_json()
    wrestling_db.save_full_log()
    
    print("Initialization complete.")

    while True:
        print("\n=== MAIN MENU ===")
        print("1. Predict Match Outcome")
        print("2. Log Manual Match Result")
        print("3. View Top 10 Pound-For-Pound Leaderboard")
        print("4. View Rankings by Weight Class")
        print("5. Exit")
        
        choice = input("Select an option (1-5): ").strip()

        if choice == '1':
            wrestler_a = input("\nEnter Wrestler A: ").strip()
            if wrestler_a not in wrestling_db.profiles:
                print(f"Wrestler '{wrestler_a}' not found in profiles.json.")
                input("\nPress Enter to return to main menu...")
                continue

            wrestler_b = input("Enter Wrestler B: ").strip()
            if wrestler_b not in wrestling_db.profiles:
                print(f"Wrestler '{wrestler_b}' not found in profiles.json.")
                input("\nPress Enter to return to main menu...")
                continue

            if wrestler_a == wrestler_b:
                print("An athlete cannot wrestle themselves.")
                input("\nPress Enter to return to main menu...")
                continue

            wrestling_db.predict_match(wrestler_a, wrestler_b)
            input("\nPress Enter to return to main menu...")

        elif choice == '2':
            print("\n--- Log Manual Match ---")
            winner = input("Winner Name: ").strip()
            w_team = input("Winner Team: ").strip()
            loser = input("Loser Name: ").strip()
            l_team = input("Loser Team: ").strip()
            weight = input("Weight Class: ").strip()
            win_type = input("Win Type (F, TF, MD, DEC): ").strip()

            if winner and loser:
                wrestling_db.process_match(winner, w_team, loser, l_team, weight, win_type)
                wrestling_db.save_profiles()
                wrestling_db.generate_athlete_json()
                print(f"Match recorded! Profiles updated and logged.")
            else:
                print("Winner and Loser names are required.")
            input("\nPress Enter to return to main menu...")

        elif choice == '3':
            wrestling_db.show_top_pfp()
            input("\nPress Enter to return to main menu...")

        elif choice == '4':
            target_weight = input("\nEnter weight class to filter (e.g., 106, 126, 150): ").strip()
            limit_str = input("How many top wrestlers do you want to view? ").strip()
            try:
                limit = int(limit_str)
            except ValueError:
                limit = 10
            wrestling_db.show_top_weight_class(target_weight, limit)
            input("\nPress Enter to return to main menu...")

        elif choice == '5' or choice.lower() in ['exit', 'q']:
            print("Exiting application. Goodbye!")
            break
        else:
            print("Invalid option selected. Please enter a choice between 1 and 5.")
            input("\nPress Enter to return to main menu...")