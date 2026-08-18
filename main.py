import os
import string
import math
import json
import re
import tkinter as tk

from tkinter import filedialog, messagebox
from nltk.stem import PorterStemmer


# ============================================================
# SETTINGS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

documents_folder = os.path.join(
    BASE_DIR,
    "documents"
)

history_file = os.path.join(
    BASE_DIR,
    "search_history.json"
)

stemmer = PorterStemmer()


# ============================================================
# GUI COLORS
# ============================================================

BG_COLOR = "#F1F5F9"
PRIMARY_COLOR = "#2563EB"
PRIMARY_DARK = "#1D4ED8"

CARD_COLOR = "#FFFFFF"
BORDER_COLOR = "#CBD5E1"

TEXT_COLOR = "#0F172A"
SECONDARY_TEXT = "#64748B"

PLACEHOLDER_COLOR = "#94A3B8"


# ============================================================
# SEARCH PLACEHOLDER
# ============================================================

SEARCH_PLACEHOLDER = "Enter keywords, phrase or topic..."


# ============================================================
# STOP WORDS
# ============================================================

stop_words = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "and",
    "or",
    "of",
    "in",
    "on",
    "to",
    "for",
    "with",
    "that",
    "this",
    "it",
    "its",
    "as",
    "by"
}


# ============================================================
# PREDEFINED DOCUMENT NAMES
# ============================================================

document_categories = {
    "France": "france.txt",
    "European Union": "european_union.txt",
    "International Law": "international_law.txt",
    "NATO": "nato.txt"
}


# ============================================================
# SEARCH ENGINE DATA
# ============================================================

document_map = {}

inverted_index = {}

word_frequencies = {}

document_frequency = {}

total_documents = 0

idf = {}

document_word_counts = {}

total_indexed_words = 0

indexed_documents = 0

total_searches = 0

search_history = []


# ============================================================
# WORD PROCESSING
# ============================================================

def normalize_word(word):
    """
    Convert a word to lowercase and apply Porter stemming.
    """

    word = word.lower().strip(string.punctuation)

    if not word:
        return ""

    return stemmer.stem(word)


def tokenize(text):
    """
    Extract words from text.
    """

    return re.findall(
        r"[A-Za-z]+(?:'[A-Za-z]+)?",
        text.lower()
    )


def normalized_tokens(text, remove_stop_words=True):
    """
    Convert text into normalized/stemmed tokens.
    """

    result = []

    for raw_word in tokenize(text):

        if (
            remove_stop_words
            and raw_word in stop_words
        ):
            continue

        word = normalize_word(raw_word)

        if word:
            result.append(word)

    return result


# ============================================================
# DOCUMENT FILES
# ============================================================

def get_document_files():
    """
    Return all TXT files inside the documents folder.
    """

    os.makedirs(
        documents_folder,
        exist_ok=True
    )

    files = []

    try:

        for filename in os.listdir(
            documents_folder
        ):

            if not filename.lower().endswith(".txt"):
                continue

            full_path = os.path.join(
                documents_folder,
                filename
            )

            if os.path.isfile(full_path):
                files.append(filename)

    except OSError as error:

        print(
            f"Could not read documents folder: {error}"
        )

    return sorted(
        files,
        key=str.lower
    )


# ============================================================
# DOCUMENT MAP
# ============================================================

def build_document_map():
    """
    Create a map between friendly document names
    and real filenames.

    Predefined documents are matched WITHOUT
    considering filename capitalization.

    Example:

        NATO -> nato.txt
        NATO -> NATO.txt
        NATO -> Nato.txt

    All of these are treated as the predefined
    NATO document.

    Every physical file is added only once.
    """

    global document_map

    document_map = {}

    files = get_document_files()

    # --------------------------------------------------------
    # Create case-insensitive lookup of real filenames
    # --------------------------------------------------------

    files_by_lowercase = {}

    for filename in files:

        files_by_lowercase[
            filename.lower()
        ] = filename

    # Keep track of files that already received
    # a friendly display name.
    mapped_files = set()

    # --------------------------------------------------------
    # PREDEFINED DOCUMENTS
    # --------------------------------------------------------

    for display_name, expected_filename in document_categories.items():

        real_filename = files_by_lowercase.get(
            expected_filename.lower()
        )

        if real_filename is not None:

            document_map[
                display_name
            ] = real_filename

            mapped_files.add(
                real_filename
            )

    # --------------------------------------------------------
    # OTHER DOCUMENTS
    # --------------------------------------------------------

    for filename in files:

        # This physical file already has a friendly name.
        if filename in mapped_files:
            continue

        display_name = os.path.splitext(
            filename
        )[0]

        original_display_name = display_name

        counter = 2

        # ----------------------------------------------------
        # Avoid duplicate display names
        # ----------------------------------------------------

        while (
            display_name.lower()
            in {
                name.lower()
                for name in document_map
            }
        ):

            display_name = (
                f"{original_display_name} ({counter})"
            )

            counter += 1

        document_map[
            display_name
        ] = filename

    # --------------------------------------------------------
    # DEBUG
    # --------------------------------------------------------

    print()
    print("DOCUMENT MAP")
    print("---------------------------------")

    for display_name, filename in document_map.items():

        print(
            f"{display_name} -> {filename}"
        )

    print("---------------------------------")


# ============================================================
# BUILD SEARCH INDEX
# ============================================================

def build_index():
    """
    Read every TXT document and create the search index.
    """

    inverted = {}

    frequencies = {}

    doc_frequency = {}

    document_word_counts_local = {}

    indexed_word_set = set()

    successful_documents = 0

    files = get_document_files()

    for filename in files:

        file_path = os.path.join(
            documents_folder,
            filename
        )

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as document:

                text = document.read()

        except UnicodeDecodeError:

            print(
                f"SKIPPED: {filename} is not UTF-8"
            )

            continue

        except OSError as error:

            print(
                f"SKIPPED: {filename}: {error}"
            )

            continue

        if not text.strip():

            print(
                f"SKIPPED: {filename} because it is empty."
            )

            continue

        words = tokenize(text)

        words_in_document = set()

        indexed_word_count = 0

        for raw_word in words:

            if raw_word in stop_words:
                continue

            word = normalize_word(
                raw_word
            )

            if not word:
                continue

            indexed_word_count += 1

            indexed_word_set.add(word)

            # ------------------------------------------------
            # INVERTED INDEX
            # ------------------------------------------------

            if word not in inverted:

                inverted[word] = []

            if filename not in inverted[word]:

                inverted[word].append(
                    filename
                )

            # ------------------------------------------------
            # WORD FREQUENCY
            # ------------------------------------------------

            if word not in frequencies:

                frequencies[word] = {}

            if filename not in frequencies[word]:

                frequencies[word][filename] = 0

            frequencies[word][filename] += 1

            # ------------------------------------------------
            # UNIQUE WORDS IN DOCUMENT
            # ------------------------------------------------

            words_in_document.add(word)

        # ----------------------------------------------------
        # DOCUMENT FREQUENCY
        # ----------------------------------------------------

        for word in words_in_document:

            doc_frequency[word] = (
                doc_frequency.get(word, 0) + 1
            )

        document_word_counts_local[
            filename
        ] = indexed_word_count

        successful_documents += 1

        print(
            f"Indexed: {filename} "
            f"({indexed_word_count} words, "
            f"{len(words_in_document)} unique)"
        )

    return (
        inverted,
        frequencies,
        doc_frequency,
        successful_documents,
        document_word_counts_local,
        indexed_word_set
    )


# ============================================================
# IDF
# ============================================================

def calculate_idf(
    doc_frequency,
    total_indexed_documents
):
    """
    Calculate inverse document frequency.

    IDF = log(N / DF)
    """

    result = {}

    if total_indexed_documents <= 0:
        return result

    for word, df in doc_frequency.items():

        if df > 0:

            result[word] = math.log(
                total_indexed_documents / df
            )

    return result


# ============================================================
# REBUILD SEARCH ENGINE
# ============================================================

def rebuild_search_engine():
    """
    Completely rebuild the search engine.
    """

    global inverted_index
    global word_frequencies
    global document_frequency
    global total_documents
    global idf
    global document_word_counts
    global total_indexed_words
    global indexed_documents

    print()
    print("=" * 60)
    print("REBUILDING SEARCH ENGINE")
    print("=" * 60)

    build_document_map()

    (
        new_inverted_index,
        new_word_frequencies,
        new_document_frequency,
        new_indexed_documents,
        new_document_word_counts,
        indexed_word_set
    ) = build_index()

    inverted_index = new_inverted_index

    word_frequencies = new_word_frequencies

    document_frequency = new_document_frequency

    indexed_documents = new_indexed_documents

    total_documents = new_indexed_documents

    document_word_counts = new_document_word_counts

    total_indexed_words = sum(
        document_word_counts.values()
    )

    idf = calculate_idf(
        document_frequency,
        total_documents
    )

    print()
    print(f"Documents indexed: {total_documents}")
    print(f"Unique indexed terms: {len(indexed_word_set)}")
    print(f"Total indexed words: {total_indexed_words}")

    print("=" * 60)


# ============================================================
# QUERY CLEANING
# ============================================================

def clean_query(query):
    """
    Convert search query into normalized words.
    """

    result = []

    for raw_word in tokenize(query):

        if raw_word in stop_words:
            continue

        word = normalize_word(
            raw_word
        )

        if (
            word
            and word not in result
        ):

            result.append(word)

    return result


# ============================================================
# EXACT PHRASE SEARCH
# ============================================================

def search_exact_phrase(
    query,
    selected_document=None
):
    """
    Search for an exact sequence of normalized words.
    """

    phrase = query.strip()

    if (
        len(phrase) >= 2
        and phrase[0] == '"'
        and phrase[-1] == '"'
    ):

        phrase = phrase[1:-1]

    normalized_phrase = clean_query(
        phrase
    )

    if not normalized_phrase:
        return set()

    found_documents = set()

    for filename in get_document_files():

        if (
            selected_document is not None
            and filename != selected_document
        ):
            continue

        file_path = os.path.join(
            documents_folder,
            filename
        )

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as document:

                text = document.read()

        except Exception:
            continue

        document_words = normalized_tokens(
            text
        )

        phrase_length = len(
            normalized_phrase
        )

        for position in range(
            len(document_words)
            - phrase_length
            + 1
        ):

            current_sequence = (
                document_words[
                    position:
                    position + phrase_length
                ]
            )

            if current_sequence == normalized_phrase:

                found_documents.add(
                    filename
                )

                break

    return found_documents


# ============================================================
# NORMAL SEARCH
# ============================================================

def search_documents(
    query,
    selected_document=None
):
    """
    Search documents using AND / OR.
    """

    query_lower = query.lower()

    # --------------------------------------------------------
    # Determine operator
    # --------------------------------------------------------

    if " and " in query_lower:

        operator = "AND"

        parts = query_lower.split(
            " and "
        )

    elif " or " in query_lower:

        operator = "OR"

        parts = query_lower.split(
            " or "
        )

    else:

        operator = "OR"

        parts = [query_lower]

    # --------------------------------------------------------
    # Normalize query
    # --------------------------------------------------------

    query_words = []

    for part in parts:

        for word in clean_query(part):

            if word not in query_words:

                query_words.append(
                    word
                )

    if not query_words:

        return set(), []

    # --------------------------------------------------------
    # AND
    # --------------------------------------------------------

    if operator == "AND":

        found_documents = None

        for word in query_words:

            documents = set(
                inverted_index.get(
                    word,
                    []
                )
            )

            if found_documents is None:

                found_documents = documents

            else:

                found_documents &= documents

        if found_documents is None:

            found_documents = set()

    # --------------------------------------------------------
    # OR
    # --------------------------------------------------------

    else:

        found_documents = set()

        for word in query_words:

            found_documents.update(
                inverted_index.get(
                    word,
                    []
                )
            )

    # --------------------------------------------------------
    # Selected document filter
    # --------------------------------------------------------

    if selected_document is not None:

        found_documents = {
            filename
            for filename in found_documents
            if filename == selected_document
        }

    return (
        found_documents,
        query_words
    )


# ============================================================
# RANKING
# ============================================================

def rank_results(
    found_documents,
    query_words
):
    """
    Rank search results using TF-IDF.
    """

    results = []

    if not query_words:
        return results

    for filename in found_documents:

        score = 0.0

        matched_words = 0

        for word in query_words:

            frequency = (
                word_frequencies
                .get(word, {})
                .get(filename, 0)
            )

            if frequency <= 0:
                continue

            matched_words += 1

            tf = 1 + math.log(
                frequency
            )

            word_idf = idf.get(
                word,
                0
            )

            tfidf = (
                tf * word_idf
            )

            if tfidf == 0:

                tfidf = (
                    0.1 * frequency
                )

            score += tfidf

        match_ratio = (
            matched_words
            / len(query_words)
        )

        final_score = (
            score
            * (1 + match_ratio)
        )

        results.append(
            (
                filename,
                final_score,
                matched_words
            )
        )

    results.sort(
        key=lambda item: (
            item[1],
            item[2]
        ),
        reverse=True
    )

    return results


# ============================================================
# SEARCH HISTORY
# ============================================================

def load_search_history():

    if not os.path.exists(
        history_file
    ):

        return []

    try:

        with open(
            history_file,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        if isinstance(data, list):

            return data

        return []

    except Exception:

        return []


def save_search_history(history):

    try:

        with open(
            history_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                history,
                file,
                ensure_ascii=False,
                indent=4
            )

    except Exception as error:

        print(
            f"Could not save search history: {error}"
        )


search_history = load_search_history()


def add_to_history(query):

    query = query.strip()

    if not query:
        return

    if query in search_history:

        search_history.remove(
            query
        )

    search_history.insert(
        0,
        query
    )

    del search_history[10:]

    save_search_history(
        search_history
    )


# ============================================================
# STATISTICS
# ============================================================

def calculate_statistics():

    statistics = {}

    # --------------------------------------------------------
    # General
    # --------------------------------------------------------

    statistics["documents"] = total_documents

    statistics["unique_terms"] = len(
        inverted_index
    )

    statistics["total_words"] = (
        total_indexed_words
    )

    if total_documents > 0:

        statistics["average_words"] = (
            total_indexed_words
            / total_documents
        )

    else:

        statistics["average_words"] = 0

    # --------------------------------------------------------
    # Search statistics
    # --------------------------------------------------------

    statistics["history_entries"] = len(
        search_history
    )

    statistics["unique_searches"] = len(
        set(search_history)
    )

    if search_history:

        search_counts = {}

        for query in search_history:

            search_counts[query] = (
                search_counts.get(query, 0)
                + 1
            )

        statistics["most_searched_query"] = max(
            search_counts,
            key=search_counts.get
        )

    else:

        statistics["most_searched_query"] = "None"

    # --------------------------------------------------------
    # Document statistics
    # --------------------------------------------------------

    document_statistics = {}

    for filename in get_document_files():

        file_path = os.path.join(
            documents_folder,
            filename
        )

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as document:

                text = document.read()

        except Exception:

            continue

        words = normalized_tokens(
            text
        )

        document_statistics[filename] = {
            "total_words": len(words),
            "unique_words": len(set(words))
        }

    statistics[
        "documents_statistics"
    ] = document_statistics

    # --------------------------------------------------------
    # Index statistics
    # --------------------------------------------------------

    terms_in_one_document = 0
    terms_in_two_documents = 0
    terms_in_three_documents = 0
    terms_in_all_documents = 0

    for word, documents in inverted_index.items():

        document_count = len(documents)

        if (
            total_documents > 0
            and document_count == total_documents
        ):

            terms_in_all_documents += 1

        elif document_count == 1:

            terms_in_one_document += 1

        elif document_count == 2:

            terms_in_two_documents += 1

        elif document_count == 3:

            terms_in_three_documents += 1

    statistics[
        "terms_in_one_document"
    ] = terms_in_one_document

    statistics[
        "terms_in_two_documents"
    ] = terms_in_two_documents

    statistics[
        "terms_in_three_documents"
    ] = terms_in_three_documents

    statistics[
        "terms_in_all_documents"
    ] = terms_in_all_documents

    # --------------------------------------------------------
    # Top terms
    # --------------------------------------------------------

    term_frequencies = []

    for (
        word,
        frequencies_by_document
    ) in word_frequencies.items():

        total_frequency = sum(
            frequencies_by_document.values()
        )

        term_frequencies.append(
            (
                word,
                total_frequency
            )
        )

    term_frequencies.sort(
        key=lambda item: (
            -item[1],
            item[0]
        )
    )

    statistics[
        "top_frequent_terms"
    ] = term_frequencies[:10]

    return statistics


# ============================================================
# DISPLAY NAME
# ============================================================

def get_display_name(filename):

    # --------------------------------------------------------
    # First check predefined documents.
    #
    # IMPORTANT:
    # Filename comparison is case-insensitive.
    # --------------------------------------------------------

    for (
        display_name,
        mapped_filename
    ) in document_categories.items():

        if (
            mapped_filename.lower()
            == filename.lower()
        ):

            return display_name

    # --------------------------------------------------------
    # Otherwise use filename without extension.
    # --------------------------------------------------------

    return os.path.splitext(
        filename
    )[0]


# ============================================================
# CATEGORY
# ============================================================

def get_selected_document():

    selected_category = (
        category_var.get()
    )

    if selected_category == "All documents":

        return None

    return document_map.get(
        selected_category
    )


def update_category_menu():
    """
    Rebuild the document dropdown.

    Every physical TXT file appears only once.

    Predefined documents such as:

        NATO -> nato.txt

    are NOT additionally shown as:

        nato
    """

    current_category = category_var.get()

    build_document_map()

    menu = category_menu["menu"]

    menu.delete(
        0,
        "end"
    )

    # --------------------------------------------------------
    # ALL DOCUMENTS
    # --------------------------------------------------------

    menu.add_command(
        label="All documents",
        command=lambda: category_var.set(
            "All documents"
        )
    )

    # --------------------------------------------------------
    # DOCUMENTS
    # --------------------------------------------------------

    for display_name in document_map:

        menu.add_command(
            label=display_name,
            command=lambda name=display_name:
                category_var.set(name)
        )

    # --------------------------------------------------------
    # RESTORE SELECTION
    # --------------------------------------------------------

    if current_category == "All documents":

        category_var.set(
            "All documents"
        )

    elif current_category in document_map:

        category_var.set(
            current_category
        )

    else:

        category_var.set(
            "All documents"
        )


# ============================================================
# SNIPPET + HIGHLIGHT
# ============================================================

def show_highlighted_snippet(
    filename,
    original_query_words
):

    file_path = os.path.join(
        documents_folder,
        filename
    )

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as document:

            text = document.read()

    except Exception:

        results_text.insert(
            tk.END,
            "   Could not read document.\n\n"
        )

        return

    position = -1

    for raw_word in original_query_words:

        clean_word = (
            raw_word
            .strip(string.punctuation)
        )

        if not clean_word:
            continue

        position = text.lower().find(
            clean_word.lower()
        )

        if position != -1:
            break

    if position == -1:

        results_text.insert(
            tk.END,
            "   No matching text found.\n\n"
        )

        return

    start = max(
        0,
        position - 70
    )

    end = min(
        len(text),
        position + 180
    )

    snippet = (
        text[start:end]
        .replace("\n", " ")
        .replace("\r", " ")
    )

    results_text.insert(
        tk.END,
        "   ..."
    )

    highlight_words = []

    for raw_word in original_query_words:

        clean_word = (
            raw_word
            .strip(string.punctuation)
            .lower()
        )

        if (
            clean_word
            and clean_word not in highlight_words
        ):

            highlight_words.append(
                clean_word
            )

    current_position = 0

    lower_snippet = snippet.lower()

    while current_position < len(snippet):

        nearest_position = None
        nearest_word = None

        for word in highlight_words:

            found_position = (
                lower_snippet.find(
                    word,
                    current_position
                )
            )

            if found_position == -1:
                continue

            if (
                nearest_position is None
                or found_position < nearest_position
            ):

                nearest_position = found_position
                nearest_word = word

        if nearest_position is None:

            results_text.insert(
                tk.END,
                snippet[current_position:]
            )

            break

        results_text.insert(
            tk.END,
            snippet[
                current_position:
                nearest_position
            ]
        )

        results_text.insert(
            tk.END,
            snippet[
                nearest_position:
                nearest_position
                + len(nearest_word)
            ],
            "highlight"
        )

        current_position = (
            nearest_position
            + len(nearest_word)
        )

    results_text.insert(
        tk.END,
        "...\n\n"
    )


# ============================================================
# STATISTICS WINDOW
# ============================================================

def show_statistics():

    try:

        rebuild_search_engine()

        update_category_menu()

        statistics = calculate_statistics()

        statistics_window = tk.Toplevel(
            window
        )

        statistics_window.title(
            "Search Engine Statistics"
        )

        statistics_window.geometry(
            "750x800"
        )

        statistics_window.minsize(
            650,
            600
        )

        statistics_window.configure(
            bg=BG_COLOR
        )

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        header = tk.Frame(
            statistics_window,
            bg=PRIMARY_COLOR,
            height=70
        )

        header.pack(
            fill=tk.X
        )

        header.pack_propagate(False)

        tk.Label(
            header,
            text="SEARCH ENGINE STATISTICS",
            font=("Arial", 18, "bold"),
            bg=PRIMARY_COLOR,
            fg="white"
        ).pack(
            pady=20
        )

        # ----------------------------------------------------
        # Text container
        # ----------------------------------------------------

        text_frame = tk.Frame(
            statistics_window,
            bg=BG_COLOR
        )

        text_frame.pack(
            fill=tk.BOTH,
            expand=True,
            padx=15,
            pady=15
        )

        scrollbar = tk.Scrollbar(
            text_frame
        )

        scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y
        )

        statistics_text = tk.Text(
            text_frame,
            font=("Courier New", 10),
            bg="white",
            fg=TEXT_COLOR,
            relief=tk.FLAT,
            yscrollcommand=scrollbar.set,
            wrap=tk.NONE
        )

        statistics_text.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True
        )

        scrollbar.config(
            command=statistics_text.yview
        )

        # ====================================================
        # GENERAL
        # ====================================================

        statistics_text.insert(
            tk.END,
            "GENERAL STATISTICS\n"
        )

        statistics_text.insert(
            tk.END,
            "-" * 50 + "\n"
        )

        statistics_text.insert(
            tk.END,
            f"Documents:              "
            f"{statistics['documents']}\n"
        )

        statistics_text.insert(
            tk.END,
            f"Unique indexed terms:   "
            f"{statistics['unique_terms']}\n"
        )

        statistics_text.insert(
            tk.END,
            f"Total indexed words:    "
            f"{statistics['total_words']}\n"
        )

        statistics_text.insert(
            tk.END,
            f"Average words/document: "
            f"{statistics['average_words']:.2f}\n\n"
        )

        # ====================================================
        # SEARCH
        # ====================================================

        statistics_text.insert(
            tk.END,
            "SEARCH STATISTICS\n"
        )

        statistics_text.insert(
            tk.END,
            "-" * 50 + "\n"
        )

        statistics_text.insert(
            tk.END,
            f"Search history entries: "
            f"{statistics['history_entries']}\n"
        )

        statistics_text.insert(
            tk.END,
            f"Unique searches:        "
            f"{statistics['unique_searches']}\n"
        )

        statistics_text.insert(
            tk.END,
            f"Most searched query:    "
            f"{statistics['most_searched_query']}\n\n"
        )

        # ====================================================
        # DOCUMENT STATISTICS
        # ====================================================

        statistics_text.insert(
            tk.END,
            "DOCUMENT STATISTICS\n"
        )

        statistics_text.insert(
            tk.END,
            "-" * 50 + "\n"
        )

        if statistics["documents_statistics"]:

            for filename, data in sorted(
                statistics[
                    "documents_statistics"
                ].items()
            ):

                display_name = get_display_name(
                    filename
                )

                statistics_text.insert(
                    tk.END,
                    f"\n{display_name}\n"
                )

                statistics_text.insert(
                    tk.END,
                    f"    File:          "
                    f"{filename}\n"
                )

                statistics_text.insert(
                    tk.END,
                    f"    Total words:   "
                    f"{data['total_words']}\n"
                )

                statistics_text.insert(
                    tk.END,
                    f"    Unique words:  "
                    f"{data['unique_words']}\n"
                )

        else:

            statistics_text.insert(
                tk.END,
                "No documents found.\n"
            )

        statistics_text.insert(
            tk.END,
            "\n"
        )

        # ====================================================
        # INDEX STATISTICS
        # ====================================================

        statistics_text.insert(
            tk.END,
            "INDEX STATISTICS\n"
        )

        statistics_text.insert(
            tk.END,
            "-" * 50 + "\n"
        )

        statistics_text.insert(
            tk.END,
            f"Terms in 1 document:    "
            f"{statistics['terms_in_one_document']}\n"
        )

        statistics_text.insert(
            tk.END,
            f"Terms in 2 documents:   "
            f"{statistics['terms_in_two_documents']}\n"
        )

        statistics_text.insert(
            tk.END,
            f"Terms in 3 documents:   "
            f"{statistics['terms_in_three_documents']}\n"
        )

        statistics_text.insert(
            tk.END,
            f"Terms in all documents: "
            f"{statistics['terms_in_all_documents']}\n\n"
        )

        # ====================================================
        # TOP TERMS
        # ====================================================

        statistics_text.insert(
            tk.END,
            "TOP 10 MOST FREQUENT TERMS\n"
        )

        statistics_text.insert(
            tk.END,
            "-" * 50 + "\n"
        )

        top_terms = statistics[
            "top_frequent_terms"
        ]

        if top_terms:

            for position, (
                word,
                frequency
            ) in enumerate(
                top_terms,
                start=1
            ):

                statistics_text.insert(
                    tk.END,
                    f"{position:>2}. "
                    f"{word:<20} "
                    f"{frequency}\n"
                )

        else:

            statistics_text.insert(
                tk.END,
                "No indexed terms found.\n"
            )

        # ====================================================
        # CHECK
        # ====================================================

        statistics_text.insert(
            tk.END,
            "\n"
        )

        statistics_text.insert(
            tk.END,
            "STATISTICS CHECK\n"
        )

        statistics_text.insert(
            tk.END,
            "-" * 50 + "\n"
        )

        df_total = (
            statistics[
                "terms_in_one_document"
            ]
            + statistics[
                "terms_in_two_documents"
            ]
            + statistics[
                "terms_in_three_documents"
            ]
            + statistics[
                "terms_in_all_documents"
            ]
        )

        statistics_text.insert(
            tk.END,
            f"Unique terms:           "
            f"{statistics['unique_terms']}\n"
        )

        statistics_text.insert(
            tk.END,
            f"DF distribution total:  "
            f"{df_total}\n"
        )

        if df_total == statistics["unique_terms"]:

            statistics_text.insert(
                tk.END,
                "Check:                  OK\n"
            )

        else:

            statistics_text.insert(
                tk.END,
                "Check:                  WARNING\n"
            )

        statistics_text.config(
            state=tk.DISABLED
        )

        # ----------------------------------------------------
        # Close
        # ----------------------------------------------------

        tk.Button(
            statistics_window,
            text="Close",
            font=("Arial", 11),
            bg=PRIMARY_COLOR,
            fg="white",
            activebackground=PRIMARY_DARK,
            activeforeground="white",
            relief=tk.FLAT,
            padx=30,
            pady=8,
            cursor="hand2",
            command=statistics_window.destroy
        ).pack(
            pady=(0, 15)
        )

        statistics_window.transient(
            window
        )

        statistics_window.grab_set()

    except Exception as error:

        print()
        print("=" * 60)
        print("STATISTICS ERROR")
        print("=" * 60)
        print(
            f"{type(error).__name__}: {error}"
        )
        print("=" * 60)

        messagebox.showerror(
            "Statistics Error",
            "The statistics window could not be opened.\n\n"
            f"{type(error).__name__}: {error}"
        )


# ============================================================
# ADD DOCUMENT
# ============================================================

def add_document():

    file_path = filedialog.askopenfilename(
        title="Select a text document",
        filetypes=[
            (
                "Text files",
                "*.txt"
            ),
            (
                "All files",
                "*.*"
            )
        ]
    )

    if not file_path:
        return

    if not file_path.lower().endswith(
        ".txt"
    ):

        messagebox.showerror(
            "Invalid file",
            "Please select a .txt file."
        )

        return

    filename = os.path.basename(
        file_path
    )

    destination = os.path.join(
        documents_folder,
        filename
    )

    if os.path.exists(
        destination
    ):

        messagebox.showwarning(
            "Document already exists",
            f"The document '{filename}' already exists."
        )

        return

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as source:

            content = source.read()

        if not content.strip():

            messagebox.showwarning(
                "Empty document",
                "The selected TXT file is empty."
            )

            return

        os.makedirs(
            documents_folder,
            exist_ok=True
        )

        with open(
            destination,
            "w",
            encoding="utf-8"
        ) as target:

            target.write(
                content
            )

        rebuild_search_engine()

        update_category_menu()

        # ----------------------------------------------------
        # Find the actual display name assigned to this file.
        # This is important for predefined documents too.
        # ----------------------------------------------------

        display_name = None

        for (
            name,
            mapped_filename
        ) in document_map.items():

            if (
                mapped_filename.lower()
                == filename.lower()
            ):

                display_name = name
                break

        if display_name is not None:

            category_var.set(
                display_name
            )

        results_text.delete(
            "1.0",
            tk.END
        )

        results_text.insert(
            tk.END,
            "Document added successfully.\n\n"
        )

        results_text.insert(
            tk.END,
            f"File: {filename}\n\n"
        )

        results_text.insert(
            tk.END,
            "The search index has been rebuilt.\n\n"
        )

        results_text.insert(
            tk.END,
            f"Documents indexed: "
            f"{total_documents}\n"
        )

        results_text.insert(
            tk.END,
            f"Indexed terms: "
            f"{len(inverted_index)}\n"
        )

        messagebox.showinfo(
            "Document added",
            f"'{filename}' was successfully added."
        )

    except UnicodeDecodeError:

        if os.path.exists(destination):

            try:
                os.remove(destination)
            except Exception:
                pass

        messagebox.showerror(
            "Encoding error",
            "The file could not be read as UTF-8."
        )

    except Exception as error:

        messagebox.showerror(
            "Error",
            f"Could not add the document:\n\n{error}"
        )


# ============================================================
# DELETE DOCUMENT
# ============================================================

def delete_document():

    files = get_document_files()

    if not files:

        messagebox.showinfo(
            "Delete Document",
            "There are no documents to delete."
        )

        return

    delete_window = tk.Toplevel(
        window
    )

    delete_window.title(
        "Delete Document"
    )

    delete_window.geometry(
        "420x340"
    )

    delete_window.resizable(
        False,
        False
    )

    delete_window.configure(
        bg=BG_COLOR
    )

    tk.Label(
        delete_window,
        text="Select a document to delete:",
        font=("Arial", 13, "bold"),
        bg=BG_COLOR,
        fg=TEXT_COLOR
    ).pack(
        pady=15
    )

    document_listbox = tk.Listbox(
        delete_window,
        width=45,
        height=10,
        font=("Arial", 11)
    )

    document_listbox.pack(
        pady=5
    )

    for filename in files:

        document_listbox.insert(
            tk.END,
            filename
        )

    def confirm_delete():

        selection = (
            document_listbox.curselection()
        )

        if not selection:

            messagebox.showwarning(
                "No document selected",
                "Please select a document first.",
                parent=delete_window
            )

            return

        filename = document_listbox.get(
            selection[0]
        )

        answer = messagebox.askyesno(
            "Confirm deletion",
            f"Are you sure you want to delete:\n\n"
            f"{filename}\n\n"
            f"This action cannot be undone.",
            parent=delete_window
        )

        if not answer:
            return

        file_path = os.path.join(
            documents_folder,
            filename
        )

        try:

            os.remove(
                file_path
            )

            rebuild_search_engine()

            update_category_menu()

            category_var.set(
                "All documents"
            )

            delete_window.destroy()

            results_text.delete(
                "1.0",
                tk.END
            )

            results_text.insert(
                tk.END,
                "Document deleted successfully.\n\n"
            )

            results_text.insert(
                tk.END,
                f"File: {filename}\n\n"
            )

            results_text.insert(
                tk.END,
                "The search index has been rebuilt.\n\n"
            )

            results_text.insert(
                tk.END,
                f"Documents indexed: "
                f"{total_documents}\n"
            )

            messagebox.showinfo(
                "Document deleted",
                f"'{filename}' was successfully deleted."
            )

        except FileNotFoundError:

            messagebox.showerror(
                "Error",
                "The selected document no longer exists.",
                parent=delete_window
            )

            rebuild_search_engine()
            update_category_menu()

        except PermissionError:

            messagebox.showerror(
                "Permission error",
                "The document is being used by another program.",
                parent=delete_window
            )

        except OSError as error:

            messagebox.showerror(
                "Error",
                f"Could not delete the document:\n\n{error}",
                parent=delete_window
            )

    buttons = tk.Frame(
        delete_window,
        bg=BG_COLOR
    )

    buttons.pack(
        pady=15
    )

    tk.Button(
        buttons,
        text="Delete",
        font=("Arial", 11),
        bg=PRIMARY_COLOR,
        fg="white",
        relief=tk.FLAT,
        padx=20,
        pady=5,
        command=confirm_delete
    ).pack(
        side=tk.LEFT,
        padx=10
    )

    tk.Button(
        buttons,
        text="Cancel",
        font=("Arial", 11),
        padx=20,
        pady=5,
        command=delete_window.destroy
    ).pack(
        side=tk.LEFT,
        padx=10
    )


# ============================================================
# UPDATE DOCUMENT
# ============================================================

def update_document():

    selected_category = (
        category_var.get()
    )

    if selected_category == "All documents":

        messagebox.showwarning(
            "Select a document",
            "Please select a specific document "
            "in 'Filter by:' before updating."
        )

        return

    filename = document_map.get(
        selected_category
    )

    if not filename:

        messagebox.showerror(
            "Document not found",
            "The selected document could not be found."
        )

        return

    destination = os.path.join(
        documents_folder,
        filename
    )

    if not os.path.isfile(
        destination
    ):

        messagebox.showerror(
            "Document not found",
            f"The document '{filename}' does not exist."
        )

        rebuild_search_engine()
        update_category_menu()

        return

    new_file_path = filedialog.askopenfilename(
        title=f"Select new content for {filename}",
        filetypes=[
            (
                "Text files",
                "*.txt"
            ),
            (
                "All files",
                "*.*"
            )
        ]
    )

    if not new_file_path:
        return

    if not new_file_path.lower().endswith(
        ".txt"
    ):

        messagebox.showerror(
            "Invalid file",
            "Please select a .txt file."
        )

        return

    try:

        with open(
            new_file_path,
            "r",
            encoding="utf-8"
        ) as source:

            new_content = source.read()

    except UnicodeDecodeError:

        messagebox.showerror(
            "Encoding error",
            "The selected file could not be read as UTF-8."
        )

        return

    except OSError as error:

        messagebox.showerror(
            "Error",
            f"Could not read the selected file:\n\n{error}"
        )

        return

    if not new_content.strip():

        messagebox.showwarning(
            "Empty document",
            "The selected file is empty."
        )

        return

    answer = messagebox.askyesno(
        "Confirm update",
        f"Are you sure you want to replace:\n\n"
        f"{filename}\n\n"
        f"with the contents of:\n\n"
        f"{os.path.basename(new_file_path)}?"
    )

    if not answer:
        return

    try:

        with open(
            destination,
            "w",
            encoding="utf-8"
        ) as target:

            target.write(
                new_content
            )

        # Verify.

        with open(
            destination,
            "r",
            encoding="utf-8"
        ) as updated_file:

            saved_content = (
                updated_file.read()
            )

        if saved_content != new_content:

            messagebox.showerror(
                "Update error",
                "The updated document could not be verified."
            )

            return

    except OSError as error:

        messagebox.showerror(
            "Update error",
            f"Could not update the document:\n\n{error}"
        )

        return

    rebuild_search_engine()

    update_category_menu()

    category_var.set(
        selected_category
    )

    results_text.delete(
        "1.0",
        tk.END
    )

    results_text.insert(
        tk.END,
        "Document updated successfully.\n\n"
    )

    results_text.insert(
        tk.END,
        f"Document: {filename}\n\n"
    )

    results_text.insert(
        tk.END,
        f"New source: "
        f"{os.path.basename(new_file_path)}\n\n"
    )

    results_text.insert(
        tk.END,
        "The search index has been completely rebuilt.\n\n"
    )

    results_text.insert(
        tk.END,
        f"Documents indexed: "
        f"{total_documents}\n"
    )

    results_text.insert(
        tk.END,
        f"Indexed terms: "
        f"{len(inverted_index)}\n"
    )

    messagebox.showinfo(
        "Document updated",
        f"'{filename}' was successfully updated."
    )


# ============================================================
# SEARCH
# ============================================================

def perform_search():

    global total_searches

    # --------------------------------------------------------
    # Get query correctly.
    #
    # The placeholder is NOT a real search query.
    # --------------------------------------------------------

    query = search_entry.get().strip()

    if query == SEARCH_PLACEHOLDER:

        query = ""

    results_text.delete(
        "1.0",
        tk.END
    )

    if not query:

        results_text.insert(
            tk.END,
            "Please enter a search query."
        )

        return

    total_searches += 1

    # --------------------------------------------------------
    # Rebuild index
    # --------------------------------------------------------

    rebuild_search_engine()

    update_category_menu()

    add_to_history(
        query
    )

    original_query_words = query.split()

    selected_category = (
        category_var.get()
    )

    selected_document = (
        get_selected_document()
    )

    # --------------------------------------------------------
    # Selected document validation
    # --------------------------------------------------------

    if (
        selected_category != "All documents"
        and selected_document is None
    ):

        results_text.insert(
            tk.END,
            "The selected document could not be found."
        )

        return

    # --------------------------------------------------------
    # Exact phrase
    # --------------------------------------------------------

    if (
        query.startswith('"')
        and query.endswith('"')
        and len(query) >= 2
    ):

        found_documents = (
            search_exact_phrase(
                query,
                selected_document
            )
        )

        query_words = clean_query(
            query[1:-1]
        )

    # --------------------------------------------------------
    # Normal search
    # --------------------------------------------------------

    else:

        (
            found_documents,
            query_words
        ) = search_documents(
            query,
            selected_document
        )

    # --------------------------------------------------------
    # No results
    # --------------------------------------------------------

    if not found_documents:

        results_text.insert(
            tk.END,
            "No documents found.\n\n"
        )

        results_text.insert(
            tk.END,
            f"Category: {selected_category}\n\n"
        )

        if selected_document is not None:

            results_text.insert(
                tk.END,
                f"Document: {selected_document}\n\n"
            )

        results_text.insert(
            tk.END,
            "Make sure the search words exist "
            "in the selected document."
        )

        return

    # --------------------------------------------------------
    # Rank
    # --------------------------------------------------------

    results = rank_results(
        found_documents,
        query_words
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    results_text.insert(
        tk.END,
        f"Category: {selected_category}\n"
    )

    results_text.insert(
        tk.END,
        f"Found {len(results)} document(s)\n\n"
    )

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    for position, (
        filename,
        score,
        matched_words
    ) in enumerate(
        results,
        start=1
    ):

        results_text.insert(
            tk.END,
            f"{position}. "
            f"{get_display_name(filename)} "
            f"({filename}) "
            f"— Score: {score:.3f}\n"
        )

        results_text.insert(
            tk.END,
            "   Matched query words: "
            f"{matched_words}/"
            f"{len(query_words)}\n"
        )

        show_highlighted_snippet(
            filename,
            original_query_words
        )


# ============================================================
# HISTORY
# ============================================================

def show_history():

    results_text.delete(
        "1.0",
        tk.END
    )

    if not search_history:

        results_text.insert(
            tk.END,
            "No recent queries."
        )

        return

    results_text.insert(
        tk.END,
        "Recent queries:\n\n"
    )

    for position, query in enumerate(
        search_history,
        start=1
    ):

        results_text.insert(
            tk.END,
            f"{position}. {query}\n"
        )


# ============================================================
# CLEAR
# ============================================================

def clear_search():

    search_entry.delete(
        0,
        tk.END
    )

    set_search_placeholder()

    category_var.set(
        "All documents"
    )

    results_text.delete(
        "1.0",
        tk.END
    )


# ============================================================
# PLACEHOLDER FUNCTIONS
# ============================================================

def set_search_placeholder():

    search_entry.delete(
        0,
        tk.END
    )

    search_entry.insert(
        0,
        SEARCH_PLACEHOLDER
    )

    search_entry.config(
        fg=PLACEHOLDER_COLOR
    )


def clear_search_placeholder(event=None):

    if search_entry.get() == SEARCH_PLACEHOLDER:

        search_entry.delete(
            0,
            tk.END
        )

        search_entry.config(
            fg=TEXT_COLOR
        )


def restore_search_placeholder(event=None):

    if not search_entry.get().strip():

        set_search_placeholder()


# ============================================================
# GUI
# ============================================================

window = tk.Tk()

window.title(
    "International Relations Search Engine"
)

window.geometry(
    "1150x820"
)

window.minsize(
    950,
    680
)

window.configure(
    bg=BG_COLOR
)


# ============================================================
# ADDITIONAL GUI COLORS
# ============================================================

HEADER_COLOR = "#2563EB"
HEADER_DARK = "#1D4ED8"

PAGE_BACKGROUND = "#F8FAFC"

WHITE = "#FFFFFF"

INPUT_BACKGROUND = "#F8FAFC"
INPUT_BORDER = "#E2E8F0"

LIGHT_BLUE = "#EFF6FF"
LIGHT_BLUE_HOVER = "#DBEAFE"

HOVER_BACKGROUND = "#F1F5F9"

SUCCESS_COLOR = "#16A34A"
DANGER_COLOR = "#DC2626"

RESULT_TITLE_COLOR = "#0F172A"
RESULT_META_COLOR = "#64748B"

HIGHLIGHT_BACKGROUND = "#FEF08A"
HIGHLIGHT_FOREGROUND = "#713F12"


# ============================================================
# TKINTER FONTS
# ============================================================

FONT_TITLE = ("Arial", 20, "bold")
FONT_SUBTITLE = ("Arial", 10)

FONT_SECTION = ("Arial", 15, "bold")
FONT_LABEL = ("Arial", 10, "bold")
FONT_NORMAL = ("Arial", 10)
FONT_SMALL = ("Arial", 9)

FONT_SEARCH = ("Arial", 13)
FONT_BUTTON = ("Arial", 10, "bold")
FONT_CHIP = ("Arial", 9, "bold")

FONT_RESULT_TITLE = ("Arial", 12, "bold")
FONT_RESULT_TEXT = ("Arial", 10)
FONT_RESULT_META = ("Arial", 9)

FONT_EMPTY_TITLE = ("Arial", 14, "bold")
FONT_EMPTY_TEXT = ("Arial", 10)


# ============================================================
# WINDOW LAYOUT
# ============================================================

main_container = tk.Frame(
    window,
    bg=PAGE_BACKGROUND
)

main_container.pack(
    fill=tk.BOTH,
    expand=True
)


# ============================================================
# HEADER
# ============================================================

header_frame = tk.Frame(
    main_container,
    bg=HEADER_COLOR,
    height=82
)

header_frame.pack(
    fill=tk.X
)

header_frame.pack_propagate(False)


# ------------------------------------------------------------
# HEADER LEFT SIDE
# ------------------------------------------------------------

header_left = tk.Frame(
    header_frame,
    bg=HEADER_COLOR
)

header_left.pack(
    side=tk.LEFT,
    fill=tk.Y,
    padx=(28, 10)
)


title_label = tk.Label(
    header_left,
    text="International Relations Search Engine",
    font=FONT_TITLE,
    bg=HEADER_COLOR,
    fg=WHITE
)

title_label.pack(
    anchor="w",
    pady=(13, 0)
)


subtitle_label = tk.Label(
    header_left,
    text="Search, analyze and explore your indexed documents",
    font=FONT_SUBTITLE,
    bg=HEADER_COLOR,
    fg="#DBEAFE"
)

subtitle_label.pack(
    anchor="w",
    pady=(2, 0)
)


# ------------------------------------------------------------
# HEADER RIGHT SIDE
# ------------------------------------------------------------

header_actions = tk.Frame(
    header_frame,
    bg=HEADER_COLOR
)

header_actions.pack(
    side=tk.RIGHT,
    padx=(10, 25)
)


def create_header_button(
    parent,
    text,
    command,
    primary=False
):

    if primary:

        button_bg = "#3B82F6"
        hover_bg = "#60A5FA"

    else:

        button_bg = "#3B82F6"
        hover_bg = "#60A5FA"

    button = tk.Button(
        parent,
        text=text,
        font=FONT_BUTTON,
        bg=button_bg,
        fg=WHITE,
        activebackground=hover_bg,
        activeforeground=WHITE,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        padx=10,
        pady=7,
        command=command
    )

    return button


# ------------------------------------------------------------
# ADD DOCUMENT
# ------------------------------------------------------------

header_add_button = create_header_button(
    header_actions,
    "+ Add",
    add_document,
    primary=True
)

header_add_button.pack(
    side=tk.LEFT,
    padx=3
)


# ------------------------------------------------------------
# UPDATE DOCUMENT
# ------------------------------------------------------------

header_update_button = create_header_button(
    header_actions,
    "↻ Update",
    update_document
)

header_update_button.pack(
    side=tk.LEFT,
    padx=3
)


# ------------------------------------------------------------
# DELETE DOCUMENT
# ------------------------------------------------------------

header_delete_button = create_header_button(
    header_actions,
    "− Delete",
    delete_document
)

header_delete_button.pack(
    side=tk.LEFT,
    padx=3
)


# ------------------------------------------------------------
# ANALYTICS
# ------------------------------------------------------------

header_analytics_button = create_header_button(
    header_actions,
    "▥ Analytics",
    show_statistics
)

header_analytics_button.pack(
    side=tk.LEFT,
    padx=3
)


# ============================================================
# MAIN CONTENT
# ============================================================

content_container = tk.Frame(
    main_container,
    bg=PAGE_BACKGROUND
)

content_container.pack(
    fill=tk.BOTH,
    expand=True
)


# ============================================================
# SEARCH CARD
# ============================================================

search_card = tk.Frame(
    content_container,
    bg=WHITE
)

search_card.pack(
    fill=tk.X,
    padx=30,
    pady=(25, 12)
)


# ------------------------------------------------------------
# SEARCH CARD INNER BORDER
# ------------------------------------------------------------

search_border = tk.Frame(
    search_card,
    bg=WHITE,
    highlightbackground="#E2E8F0",
    highlightthickness=1
)

search_border.pack(
    fill=tk.X
)


# ============================================================
# SEARCH TITLE
# ============================================================

search_title_frame = tk.Frame(
    search_border,
    bg=WHITE
)

search_title_frame.pack(
    fill=tk.X,
    padx=22,
    pady=(18, 0)
)


search_title = tk.Label(
    search_title_frame,
    text="Explore the knowledge base",
    font=FONT_SECTION,
    bg=WHITE,
    fg=TEXT_COLOR
)

search_title.pack(
    anchor="w"
)


search_description = tk.Label(
    search_title_frame,
    text="Search across your indexed international relations documents.",
    font=FONT_SMALL,
    bg=WHITE,
    fg=SECONDARY_TEXT
)

search_description.pack(
    anchor="w",
    pady=(3, 0)
)


# ============================================================
# SEARCH INPUT ROW
# ============================================================

search_row = tk.Frame(
    search_border,
    bg=WHITE
)

search_row.pack(
    fill=tk.X,
    padx=22,
    pady=(15, 8)
)


# ------------------------------------------------------------
# SEARCH ENTRY CONTAINER
# ------------------------------------------------------------

search_entry_container = tk.Frame(
    search_row,
    bg=INPUT_BACKGROUND,
    highlightbackground=INPUT_BORDER,
    highlightthickness=1
)

search_entry_container.pack(
    side=tk.LEFT,
    fill=tk.X,
    expand=True,
    ipady=1
)


# ------------------------------------------------------------
# SEARCH ICON
# ------------------------------------------------------------

search_icon = tk.Label(
    search_entry_container,
    text="⌕",
    font=("Arial", 20),
    bg=INPUT_BACKGROUND,
    fg=SECONDARY_TEXT
)

search_icon.pack(
    side=tk.LEFT,
    padx=(12, 5)
)


# ------------------------------------------------------------
# SEARCH ENTRY
# ------------------------------------------------------------

search_entry = tk.Entry(
    search_entry_container,
    font=FONT_SEARCH,
    relief=tk.FLAT,
    bd=0,
    bg=INPUT_BACKGROUND,
    fg=TEXT_COLOR,
    insertbackground=TEXT_COLOR
)

search_entry.pack(
    side=tk.LEFT,
    fill=tk.X,
    expand=True,
    ipady=10,
    padx=(2, 12)
)


# ------------------------------------------------------------
# PLACEHOLDER
# ------------------------------------------------------------

set_search_placeholder()


search_entry.bind(
    "<FocusIn>",
    clear_search_placeholder
)

search_entry.bind(
    "<FocusOut>",
    restore_search_placeholder
)


# ============================================================
# FIND BUTTON
# ============================================================

search_button = tk.Button(
    search_row,
    text="Find Documents",
    font=FONT_BUTTON,
    bg=PRIMARY_COLOR,
    fg=WHITE,
    activebackground=PRIMARY_DARK,
    activeforeground=WHITE,
    relief=tk.FLAT,
    bd=0,
    highlightthickness=0,
    cursor="hand2",
    padx=25,
    pady=12,
    command=perform_search
)

search_button.pack(
    side=tk.RIGHT,
    padx=(12, 0)
)


# ============================================================
# FILTER ROW
# ============================================================

filter_row = tk.Frame(
    search_border,
    bg=WHITE
)

filter_row.pack(
    fill=tk.X,
    padx=22,
    pady=(4, 18)
)


# ------------------------------------------------------------
# FILTER LABEL
# ------------------------------------------------------------

category_label = tk.Label(
    filter_row,
    text="Search in",
    font=FONT_LABEL,
    bg=WHITE,
    fg=SECONDARY_TEXT
)

category_label.pack(
    side=tk.LEFT,
    padx=(0, 10)
)


# ============================================================
# CATEGORY VARIABLE
# ============================================================

category_var = tk.StringVar(
    value="All documents"
)


# ============================================================
# CATEGORY MENU
# ============================================================

category_menu = tk.OptionMenu(
    filter_row,
    category_var,
    "All documents"
)

category_menu.config(
    font=FONT_NORMAL,
    bg=INPUT_BACKGROUND,
    fg=TEXT_COLOR,
    activebackground=LIGHT_BLUE,
    activeforeground=TEXT_COLOR,
    relief=tk.FLAT,
    bd=0,
    highlightbackground=INPUT_BORDER,
    highlightthickness=1,
    cursor="hand2",
    padx=10,
    pady=5,
    indicatoron=True
)

category_menu.pack(
    side=tk.LEFT
)


# ------------------------------------------------------------
# STYLE OPTIONMENU INTERNAL MENU
# ------------------------------------------------------------

try:

    category_menu["menu"].config(
        font=FONT_NORMAL,
        bg=WHITE,
        fg=TEXT_COLOR,
        activebackground=LIGHT_BLUE,
        activeforeground=TEXT_COLOR,
        borderwidth=0,
        relief=tk.FLAT
    )

except Exception:
    pass


# ============================================================
# SEARCH ACTIONS
# ============================================================

search_actions = tk.Frame(
    filter_row,
    bg=WHITE
)

search_actions.pack(
    side=tk.RIGHT
)


# ------------------------------------------------------------
# CHIP BUTTON
# ------------------------------------------------------------

def create_chip_button(
    parent,
    text,
    command,
    accent=False
):

    if accent:

        background = LIGHT_BLUE
        foreground = PRIMARY_COLOR
        active_background = LIGHT_BLUE_HOVER

    else:

        background = WHITE
        foreground = SECONDARY_TEXT
        active_background = HOVER_BACKGROUND

    button = tk.Button(
        parent,
        text=text,
        font=FONT_CHIP,
        bg=background,
        fg=foreground,
        activebackground=active_background,
        activeforeground=foreground,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        padx=12,
        pady=6,
        command=command
    )

    return button


# ============================================================
# RECENT QUERIES
# ============================================================

history_button = create_chip_button(
    search_actions,
    "Recent Queries",
    show_history,
    accent=True
)

history_button.pack(
    side=tk.LEFT,
    padx=(0, 6)
)


# ============================================================
# CLEAR
# ============================================================

clear_button = create_chip_button(
    search_actions,
    "Clear",
    clear_search
)

clear_button.pack(
    side=tk.LEFT
)


# ============================================================
# RESULTS SECTION
# ============================================================

results_section = tk.Frame(
    content_container,
    bg=PAGE_BACKGROUND
)

results_section.pack(
    fill=tk.BOTH,
    expand=True,
    padx=30,
    pady=(0, 25)
)


# ============================================================
# RESULTS HEADER
# ============================================================

results_header = tk.Frame(
    results_section,
    bg=PAGE_BACKGROUND
)

results_header.pack(
    fill=tk.X,
    pady=(2, 8)
)


results_title = tk.Label(
    results_header,
    text="Search Results",
    font=("Arial", 14, "bold"),
    bg=PAGE_BACKGROUND,
    fg=TEXT_COLOR
)

results_title.pack(
    side=tk.LEFT
)


results_status = tk.Label(
    results_header,
    text="Ready",
    font=FONT_SMALL,
    bg=PAGE_BACKGROUND,
    fg=SECONDARY_TEXT
)

results_status.pack(
    side=tk.RIGHT
)


# ============================================================
# RESULTS CARD
# ============================================================

results_card = tk.Frame(
    results_section,
    bg=WHITE,
    highlightbackground="#E2E8F0",
    highlightthickness=1
)

results_card.pack(
    fill=tk.BOTH,
    expand=True
)


# ============================================================
# RESULTS SCROLLBAR
# ============================================================

results_scrollbar = tk.Scrollbar(
    results_card,
    orient=tk.VERTICAL
)

results_scrollbar.pack(
    side=tk.RIGHT,
    fill=tk.Y
)


# ============================================================
# RESULTS TEXT
# ============================================================

results_text = tk.Text(
    results_card,
    font=FONT_RESULT_TEXT,
    bg=WHITE,
    fg=TEXT_COLOR,
    relief=tk.FLAT,
    bd=0,
    highlightthickness=0,
    wrap=tk.WORD,
    padx=24,
    pady=20,
    spacing1=2,
    spacing2=2,
    spacing3=8,
    yscrollcommand=results_scrollbar.set
)

results_text.pack(
    side=tk.LEFT,
    fill=tk.BOTH,
    expand=True
)


results_scrollbar.config(
    command=results_text.yview
)


# ============================================================
# RESULT TEXT TAGS
# ============================================================

results_text.tag_config(
    "result_title",
    font=FONT_RESULT_TITLE,
    foreground=RESULT_TITLE_COLOR
)

results_text.tag_config(
    "result_meta",
    font=FONT_RESULT_META,
    foreground=RESULT_META_COLOR
)

results_text.tag_config(
    "result_score",
    font=("Arial", 10, "bold"),
    foreground=PRIMARY_COLOR
)

results_text.tag_config(
    "result_success",
    font=("Arial", 10, "bold"),
    foreground=SUCCESS_COLOR
)

results_text.tag_config(
    "result_warning",
    font=("Arial", 10, "bold"),
    foreground=DANGER_COLOR
)

results_text.tag_config(
    "empty_title",
    font=FONT_EMPTY_TITLE,
    foreground=TEXT_COLOR,
    justify="center"
)

results_text.tag_config(
    "empty_text",
    font=FONT_EMPTY_TEXT,
    foreground=SECONDARY_TEXT,
    justify="center"
)

results_text.tag_config(
    "highlight",
    background=HIGHLIGHT_BACKGROUND,
    foreground=HIGHLIGHT_FOREGROUND
)


# ============================================================
# EMPTY STATE
# ============================================================

def show_empty_state():

    results_text.config(
        state=tk.NORMAL
    )

    results_text.delete(
        "1.0",
        tk.END
    )

    results_text.insert(
        tk.END,
        "\n\n"
    )

    results_text.insert(
    tk.END,
    "🔍\n",
    "empty_title"
)

    results_text.insert(
        tk.END,
        "Start searching\n",
        "empty_title"
    )

    results_text.insert(
        tk.END,
        "\n"
    )

    results_text.insert(
        tk.END,
        "Enter a query above to search your indexed documents.\n",
        "empty_text"
    )

    results_text.insert(
        tk.END,
        "You can search all documents or select a specific document.\n",
        "empty_text"
    )

    results_text.config(
        state=tk.DISABLED
    )


# ============================================================
# SAFE RESULTS WRITER
# ============================================================

def prepare_results_for_writing():

    results_text.config(
        state=tk.NORMAL
    )


# ============================================================
# IMPROVE STATUS AFTER SEARCH
# ============================================================

_original_perform_search = perform_search


def perform_search_with_status():

    query = search_entry.get().strip()

    if query == SEARCH_PLACEHOLDER:
        query = ""

    if not query:

        results_status.config(
            text="Enter a query"
        )

        show_empty_state()

        return

    results_status.config(
        text="Searching..."
    )

    results_text.config(
        state=tk.NORMAL
    )

    results_text.delete(
        "1.0",
        tk.END
    )

    # --------------------------------------------------------
    # Run the original search function.
    # --------------------------------------------------------

    try:

        _original_perform_search()

    except Exception as error:

        results_text.config(
            state=tk.NORMAL
        )

        results_text.delete(
            "1.0",
            tk.END
        )

        results_text.insert(
            tk.END,
            "Search error\n\n",
            "result_warning"
        )

        results_text.insert(
            tk.END,
            f"{type(error).__name__}: {error}"
        )

        results_status.config(
            text="Search error"
        )

        return

    # --------------------------------------------------------
    # Determine whether results exist.
    # --------------------------------------------------------

    content = results_text.get(
        "1.0",
        tk.END
    ).strip()

    if not content:

        results_status.config(
            text="No results"
        )

        show_empty_state()

        return

    if content.startswith(
        "No documents found"
    ):

        results_status.config(
            text="No results"
        )

    elif content.startswith(
        "Please enter"
    ):

        results_status.config(
            text="Enter a query"
        )

    else:

        # ----------------------------------------------------
        # Try to extract number of results from original output.
        # ----------------------------------------------------

        match = re.search(
            r"Found\s+(\d+)\s+document",
            content
        )

        if match:

            count = match.group(1)

            results_status.config(
                text=f"{count} result(s)"
            )

        else:

            results_status.config(
                text="Results found"
            )


# ============================================================
# REPLACE SEARCH BUTTON COMMAND
# ============================================================

search_button.config(
    command=perform_search_with_status
)


# ============================================================
# ENTER KEY
# ============================================================

search_entry.bind(
    "<Return>",
    lambda event: perform_search_with_status()
)


# ============================================================
# CLEAR SEARCH OVERRIDE
# ============================================================

_original_clear_search = clear_search


def clear_search_with_status():

    _original_clear_search()

    results_status.config(
        text="Ready"
    )

    show_empty_state()


clear_button.config(
    command=clear_search_with_status
)


# ============================================================
# HISTORY OVERRIDE
# ============================================================

_original_show_history = show_history


def show_history_with_status():

    results_text.config(
        state=tk.NORMAL
    )

    _original_show_history()

    results_status.config(
        text="Search history"
    )


history_button.config(
    command=show_history_with_status
)


# ============================================================
# DOCUMENT ACTION STATUS HELPERS
# ============================================================

def refresh_after_document_action():

    try:

        rebuild_search_engine()
        update_category_menu()

    except Exception as error:

        print(
            f"Could not refresh search engine: {error}"
        )


# ============================================================
# INITIAL EMPTY STATE
# ============================================================

show_empty_state()


# ============================================================
# START SEARCH ENGINE
# ============================================================

os.makedirs(
    documents_folder,
    exist_ok=True
)

rebuild_search_engine()

update_category_menu()

show_empty_state()


# ============================================================
# WINDOW SHORTCUTS
# ============================================================

def focus_search(event=None):

    search_entry.focus_set()

    if search_entry.get() == SEARCH_PLACEHOLDER:

        clear_search_placeholder()


window.bind(
    "<Control-f>",
    focus_search
)


# ============================================================
# WINDOW CLOSE
# ============================================================

def close_application():

    try:

        save_search_history(
            search_history
        )

    except Exception:
        pass

    window.destroy()


window.protocol(
    "WM_DELETE_WINDOW",
    close_application
)


# ============================================================
# START GUI
# ============================================================

window.mainloop()