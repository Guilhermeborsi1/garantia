{
    "name": "Garantia",
    "version": "1.0.0",
    "author": "Guilherme Borsi",
    "license": "AGPL-3",
    "category": "Sales",
    "summary": "Módulo para gerenciamento de garantias",
    "description": """
Módulo para gerenciamento e controle de garantias de produtos e serviços.
""",
    "depends": ["base", "product"],
    "data": [
        "views/garantia_views.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": True,
}