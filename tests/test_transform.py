from painel.transform import extract_skills, is_data_role, seniority, work_mode


def test_skills():
    s = extract_skills("Buscamos analista con Power BI, SQL y Python. Valorable R y Excel.")
    assert {"Power BI", "SQL", "Python", "R", "Excel"} <= set(s)


def test_skills_no_false_matches():
    assert "Java" not in extract_skills("Experiencia con JavaScript")
    assert "R" not in extract_skills("Trabajo en equipo, Responsable de Recursos")


def test_seniority():
    assert seniority("Data Analyst Junior") == "junior"
    assert seniority("Senior Data Engineer") == "senior"
    assert seniority("Analista de datos") == "unspecified"


def test_work_mode():
    assert work_mode("Puesto 100% remoto") == "remote"
    assert work_mode("Modelo híbrido, 2 días en oficina") == "hybrid"
    assert work_mode("Oficina en Elche") == "not stated"


def test_data_role():
    assert is_data_role("Analista de datos BI")
    assert not is_data_role("Comercial de ventas")


def test_generic_analyst_is_not_data():
    assert not is_data_role("Analista de Procesos y Mejora Continua")
    assert is_data_role("Analista de datos y Reporting")
    assert is_data_role("BI Analyst")


def test_known_false_positives():
    assert not is_data_role("Data Center Technician - Elche")
    assert not is_data_role("Sneaker Product Buyer - Data-Driven")
