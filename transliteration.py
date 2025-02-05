import yaml

def load_transliteration_rules(yaml_file):
    """Load transliteration rules from the YAML file."""
    with open(yaml_file, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)
        return data.get('transliteration', [])

def load_input_words(input_file):
    """Load input words from a text file."""
    with open(input_file, 'r', encoding='utf-8') as file:
        words = [line.strip() for line in file if line.strip()]
    return words

def identify_transliteration_type(word, rules):
    """Identify transliteration type based on script group and specific markers."""
    # Define sets of Latin and Cyrillic characters
    latin_chars = set("abcdefghijklmnopqrstuvwxyzšșśrz")
    cyrillic_chars = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюяљњјћџ")
    
    # Check if the word is primarily Latin or Cyrillic
    if any(char in latin_chars for char in word):
        script_group = 'latin'
    elif any(char in cyrillic_chars for char in word):
        script_group = 'cyrillic'
    else:
        return None  # No recognizable script

    # Apply specific rules based on the identified script group
    for rule in rules:
        if rule['script'] != script_group:
            continue
        
        alphabet = {item['from']: i}tem['to'] for item in rule['alphabet']
        script = rule['script']
        variant = rule['variant']
        
        # Latin-1: Contains diacritics like ș, š, ś
        if script == 'latin' and variant == 1 and any(char in ['ș', 'š', 'ś', 'ļ'] for char in word):
            return rule
        
        # Latin-2: Contains digraphs like rz, excludes diacritics
        if script == 'latin' and variant == 2 and any(digraph in word for digraph in ['rz', 'r', 'z', 'ch', 'sh', 'th', 'lh']) and not any(char in ['ș', 'š', 'ś', 'ļ'] for char in word):
            return rule
        
        # Cyrillic-1: Contains т, ь, ъ, э
        if script == 'cyrillic' and variant == 1 and any(char in ['т', 'ь', 'ъ', 'э'] for char in word):
            return rule
        
        # Cyrillic-2: Contains ф, е, ј
        if script == 'cyrillic' and variant == 2 and any(char in ['ф', 'е', 'ј'] for char in word):
            return rule
    
    return None  # Default case if no match is found

def transliterate_word(word, transliteration_rule):
    """Transliterate a word based on the given transliteration rule."""
    alphabet = {item['from']: item['to'] for item in transliteration_rule['alphabet']}
    transliterated_word = ""
    
    i = 0
    while i < len(word):
        match_found = False
        
        # Try matching longer sequences first
        for length in range(2, 0, -1):
            if i + length <= len(word):
                segment = word[i:i + length]
                if segment in alphabet:
                    transliterated_word += alphabet[segment]
                    i += length
                    match_found = True
                    break
        
        if not match_found:
            # If no match, append the character as-is and move forward
            transliterated_word += word[i]
            i += 1
    
    return transliterated_word

def process_words(words, transliteration_rules):
    """Process each word and apply transliteration rules."""
    results = {}
    for word in words:
        transliterations = {}
        transliteration_rule = identify_transliteration_type(word, transliteration_rules)
        if transliteration_rule:
            transliterated_word = transliterate_word(word, transliteration_rule)
            transliterations['Script'] = transliteration_rule['script']
            transliterations['Variant'] = transliteration_rule['variant']
            transliterations['Transliterated'] = transliterated_word
        else:
            transliterations['Error'] = "Could not be classified or transliterated."
        results[word] = transliterations
    return results

def main():
    yaml_file = 'phonology.yaml'  # Path to your YAML file
    input_file = 'input_words.txt'  # Input file containing words
    output_file = 'transliterations.txt'  # Output file
    
    # Load transliteration rules
    transliteration_rules = load_transliteration_rules(yaml_file)

    # Load input words
    words = load_input_words(input_file)
    # Process words
    results = process_words(words, transliteration_rules)

    # Save results
    with open(output_file, 'w', encoding='utf-8') as file:
        for word, transliterations in results.items():
            file.write(f"Input word: {word}\n")
            for key, value in transliterations.items():
                file.write(f"  {key}: {value}\n")
            file.write("\n\n")  # Separate entries for readability
    print(f"Transliterations saved to {output_file}")

if __name__ == "__main__":
    main()
