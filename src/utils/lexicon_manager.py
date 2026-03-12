import json

class LexiconManager:
    def __init__(self, path):
        self.path = path
        self.lexicon = self.load()

    def load(self):
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"File not found: {self.path}")
            return []
        except json.JSONDecodeError:
            print(f"Invalid JSON in file: {self.path}")
            return []
        
    def save(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.lexicon, f, ensure_ascii=False, indent=2)

    def get_terms(self):
        return [item["term"] for item in self.lexicon]
    
    def add_term(self, term, weight=1.0):
        
        term = term.strip()
        for item in self.lexicon:
            if item["term"] == term:
                if item["weight"] != weight:
                    item["weight"] = weight
                    self.save()   
                    print(f"Updated weight for term '{term}' to {weight}")
                    return True             
                
                print(f"Term '{term}' already exists")
                return False
            
        self.lexicon.append({"term": term, "weight": weight})
        self.save()
        return True

    def delete_term(self, term):
        self.lexicon = [item for item in self.lexicon if item["term"] != term]
        self.save()

    def update_weight(self, term, weight):
        for item in self.lexicon:
            if item["term"] == term:
                item["weight"] = weight
                self.save()
                return
        print("Term not found")