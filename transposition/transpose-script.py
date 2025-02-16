import re

def classify_word(word):
    latin_special = "ļșśš"
    latin_combinations = ["sh", "th", "rz", "ch"]
    cyrillic_class_3 = "ьэщъ"
    cyrillic_class_4 = "је"
    
    if re.search(r'[a-zA-Z]', word):  # Latin check
        if any(char in word for char in latin_special):
            return 1
        elif any(combo in word for combo in latin_combinations):
            return 2
        else:
            return 1  # Default to class 1
    elif re.search(r'[а-яА-ЯёЁ]', word):  # Cyrillic check
        if any(char in word for char in cyrillic_class_3):
            return 3
        elif any(char in word for char in cyrillic_class_4):
            return 4
        else:
            return 3  # Default to class 3
    else:
        return None  # Unclassified (if needed for debugging)

def process_file(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        words = f.read().split()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for word in words:
            classification = classify_word(word)
            if classification is not None:
                f.write(f"{word} {classification}\n")

# Example usage
input_filename = "input.txt"
output_filename = "output.txt"
process_file(input_filename, output_filename)
