# Lexicon Views

## All verbs (type 2)
```dataview
TABLE lemma, script.latin AS latin, meaning
FROM "Lexicon"
WHERE pos = "verbs" AND verb_type = "2"
SORT lemma ASC
```

## All nouns with class link
```dataview
TABLE lemma, meaning, noun_class
FROM "Lexicon"
WHERE pos = "nouns"
SORT lemma ASC
```

## Contains phoneme 'x'
```dataview
TABLE lemma, meaning
FROM "Lexicon"
WHERE contains(script.latin, "x")
```

## Everything
```dataview
TABLE pos, lemma, meaning
FROM "Lexicon"
SORT pos, lemma
```
