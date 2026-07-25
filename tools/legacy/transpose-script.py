import re

# alphabetic order: t s c g q j h ś ș š l ļ x i e a

# Define character mappings for each class
class_1 = ["śś", "șș", "šš", "ļļ", "tt", "ss", "cc", "gg", "qq", "jj", "hh", "ll", "xx", "ś", "ș", "š", "ļ", "t", "s", "c", "g", "q", "j", "h", "l", "x", "i", "e", "a"]
class_2 = ["cch", "ssh", "rrz", "llh", "tth", "ss", "cc", "gg", "qq", "jj", "hh", "ll", "xx", "ch", "sh", "rz", "lh", "t", "s", "c", "g", "q", "j", "h", "l", "x", "i", "e", "a"]
class_3 = ["щщ", "шш", "жж", "лль", "тт", "сс", "ссь", "гг", "кк", "ххь", "ьь", "лл", "хх", "щ", "ш", "ж", "ль", "т", "с", "сь", "г", "к", "хь", "ь", "л", "х", "и", "э", "а"]
class_4 = ["шшј", "шш", "жж", "ллј", "фф", "сс", "ссј", "гг", "кк", "јј", "??", "лл", "хх", "шј", "ш", "ж", "лј", "ф", "с", "сј", "г", "к", "ј", "?", "л","х", "и", "е", "а"]

transposition_table = [class_1, class_2, class_3, class_4]

# Step 1: Classify word
def classify_word(word):
    latin_chars = re.compile(r"[a-zA-Z]")
    cyrillic_chars = re.compile(r"[а-яА-Я]")

    if latin_chars.search(word):
        if any(char in word for char in ["ļ", "ș", "ś", "š"]):
            return 1
        if any(seq in word for seq in ["sh", "th", "rz", "ch"]):
            return 2
        return 1  # Default for Latin

    if cyrillic_chars.search(word):
        if any(char in word for char in ["ь", "э", "щ", "ъ"]):
            return 3
        if any(char in word for char in ["ј", "е"]):
            return 4
        return 3  # Default for Cyrillic

    return 1  # If unknown, assume Latin (Class 1)

# Step 2: Transpose word into all four classes
def transpose_word(word, original_class):
    transposed_versions = [""] * 4  # Placeholder for class 1–4 words
    transposed_versions[original_class - 1] = word  # Keep original for its class

    for target_class in range(4):
        if target_class == original_class - 1:
            continue  # Skip original class

        new_word = word
        original_list = transposition_table[original_class - 1]
        target_list = transposition_table[target_class]

        # Replace step-by-step (double consonants → single consonants → vowels)
        for i in range(len(original_list)):
            new_word = new_word.replace(original_list[i], target_list[i])

        transposed_versions[target_class] = new_word

    return transposed_versions

# Step 3: Process file
def process_file(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        words = f.read().split()

    with open(output_file, 'w', encoding='utf-8') as f:
        for word in words:
            original_class = classify_word(word)
            transposed_words = transpose_word(word, original_class)

            f.write(f"{word} ({original_class}):\n")
            for i in range(4):
                f.write(f"{i+1}. {transposed_words[i]}\n")
            f.write("\n")  # Blank line for readability

# Run script
input_filename = "input.txt"
output_filename = "output.txt"
process_file(input_filename, output_filename)

print("Processing complete! Check output.txt for results.")
