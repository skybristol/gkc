"""Tests for validate_monolingualtext coercion and language code normalization."""

from gkc.fermenter import validate_monolingualtext

# ---------------------------------------------------------------------------
# Happy path — well-formed canonical input
# ---------------------------------------------------------------------------


def test_valid_canonical_dict():
    result = validate_monolingualtext({"language": "en", "text": "Cherokee Nation"})

    assert result.valid is True
    assert result.value == {"language": "en", "text": "Cherokee Nation"}
    assert result.errors == []
    assert result.uncertainty == 0.0


def test_valid_mul_language_code():
    result = validate_monolingualtext({"language": "mul", "text": "Some text"})

    assert result.valid is True
    assert result.value["language"] == "mul"


def test_valid_regional_variant_code():
    result = validate_monolingualtext({"language": "zh-hans", "text": "汉字"})

    assert result.valid is True
    assert result.value["language"] == "zh-hans"


def test_valid_zxx_no_linguistic_content():
    result = validate_monolingualtext({"language": "zxx", "text": "N/A"})

    assert result.valid is True
    assert result.value["language"] == "zxx"


# ---------------------------------------------------------------------------
# Coercion — plain string input
# ---------------------------------------------------------------------------


def test_plain_string_coerced_to_mul():
    result = validate_monolingualtext("Cherokee Nation")

    assert result.valid is True
    assert result.value == {"language": "mul", "text": "Cherokee Nation"}
    assert result.uncertainty == 0.5
    assert any("mul" in w for w in result.warnings)


def test_plain_string_empty_fails():
    result = validate_monolingualtext("   ")

    assert result.valid is False
    assert any("empty" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Coercion — key normalization
# ---------------------------------------------------------------------------


def test_lang_key_renamed_to_language():
    result = validate_monolingualtext({"lang": "fr", "text": "Bonjour"})

    assert result.valid is True
    assert result.value == {"language": "fr", "text": "Bonjour"}
    assert any("lang" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Language alias normalization (ISO 639-2 and English names)
# ---------------------------------------------------------------------------


def test_three_letter_code_eng_normalized():
    result = validate_monolingualtext({"language": "eng", "text": "Hello"})

    assert result.valid is True
    assert result.value["language"] == "en"
    assert result.uncertainty > 0


def test_three_letter_code_fra_normalized():
    result = validate_monolingualtext({"language": "fra", "text": "Bonjour"})

    assert result.valid is True
    assert result.value["language"] == "fr"


def test_three_letter_bibliographic_fre_normalized():
    result = validate_monolingualtext({"language": "fre", "text": "Bonjour"})

    assert result.valid is True
    assert result.value["language"] == "fr"


def test_english_name_normalized():
    result = validate_monolingualtext({"language": "english", "text": "Hello"})

    assert result.valid is True
    assert result.value["language"] == "en"
    assert any("normalized" in w for w in result.warnings)


def test_german_name_normalized():
    result = validate_monolingualtext({"language": "german", "text": "Hallo"})

    assert result.valid is True
    assert result.value["language"] == "de"


def test_cherokee_three_letter_preserved():
    result = validate_monolingualtext({"language": "chr", "text": "ᎠᏂᏴᏫᏯ"})

    assert result.valid is True
    assert result.value["language"] == "chr"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_null_value_fails():
    result = validate_monolingualtext(None)

    assert result.valid is False
    assert any("null" in e for e in result.errors)


def test_non_dict_non_string_fails():
    result = validate_monolingualtext(42)

    assert result.valid is False
    assert any("dict or string" in e for e in result.errors)


def test_missing_text_field_fails():
    result = validate_monolingualtext({"language": "en"})

    assert result.valid is False
    assert any("text" in e for e in result.errors)


def test_missing_language_field_fails():
    result = validate_monolingualtext({"text": "Hello"})

    assert result.valid is False
    assert any("language" in e for e in result.errors)


def test_empty_text_field_fails():
    result = validate_monolingualtext({"language": "en", "text": ""})

    assert result.valid is False
    assert any("empty" in e for e in result.errors)


def test_non_string_language_fails():
    result = validate_monolingualtext({"language": 123, "text": "Hello"})

    assert result.valid is False
    assert any("string" in e for e in result.errors)


def test_non_string_text_fails():
    result = validate_monolingualtext({"language": "en", "text": ["Hello"]})

    assert result.valid is False
    assert any("string" in e for e in result.errors)


def test_invalid_language_code_fails():
    result = validate_monolingualtext(
        {"language": "not-a-valid-code!!!", "text": "Hello"}
    )

    assert result.valid is False
    assert any("BCP-47" in e for e in result.errors)


def test_numeric_language_code_fails():
    result = validate_monolingualtext({"language": "123", "text": "Hello"})

    assert result.valid is False
    assert any("BCP-47" in e for e in result.errors)
