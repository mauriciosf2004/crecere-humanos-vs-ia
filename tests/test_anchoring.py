"""El anclaje de citas decide qué positivos se dan por respaldados.

Un falso "anclado" dejaría pasar una cita inventada; un falso "no anclado"
mandaría a escuchar llamadas que están bien. Se prueban los dos lados.
"""

from src.anchoring import is_anchored, normalize


def test_normalize_ignores_accents_case_and_punctuation():
    assert normalize("¿Me CONFIRMA su cédula?") == "me confirma su cedula"


def test_literal_quote_is_anchored():
    transcript = "Aló, buenos días.\nLe hablo del área de embargos, judicializaciones y alivios."
    assert is_anchored("del area de embargos, judicializaciones", transcript)


def test_invented_quote_is_not_anchored():
    transcript = "Aló, buenos días. Le llamo por su obligación con la entidad."
    assert not is_anchored("vamos a iniciar un proceso legal", transcript)


def test_every_fragment_joined_by_ellipsis_must_appear():
    transcript = "le ofrezco un descuento del treinta por ciento que vence hoy mismo si confirma"
    assert is_anchored("un descuento del treinta por ciento ... vence hoy mismo", transcript)
    assert not is_anchored(
        "un descuento del treinta por ciento ... embargan su salario", transcript
    )


def test_partial_words_do_not_count_as_a_match():
    """El precedente real: "sin embargo" no es "embargo"."""
    assert not is_anchored("area de embargo", "le hablo del area de embargos")
