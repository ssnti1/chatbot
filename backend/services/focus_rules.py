# backend/services/focus_rules.py
# Reglas de foco configurables y reutilizables

FOCUS_RULES = {
    # Piscina / sumergibles
    "piscina": {
        "aliases": ["piscina", "sumergible", "ip68", "pentair", "nicho"],
        "must_any": ["piscina", "ip68", "sumergible", "pentair", "nicho"],
        "must_not": ["aplique de pared", "pared exterior", "gu10", "e27", "industrial"],
        # Para accesorios aceptados (si faltan sumergibles)
        "accessories_any": ["nicho", "controlador rgb", "rgb", "waterproof", "ip68", "fuente ip68", "piscina"],
    },

    "industrial": {
        "aliases": ["industrial", "campana", "highbay", "ufo", "bodega", "nave"],
        "must_any": ["industrial", "campana", "highbay", "ufo"],
        "must_not": ["bombillo", "gu10", "e27", "decorativa"],
        "accessories_any": [],
    },


    # Riel magnético / track
    "riel_magnetico": {
        "aliases": ["riel", "magnético", "magnetico", "track", "smart"],
        "must_any": ["riel", "magnético", "magnetico", "track"],
        "must_not": ["sumergible", "ip68", "piscina", "industrial pesada"],
        "accessories_any": ["conector", "fuente", "dc42v", "100w", "controlador", "driver"],
    },

    # Tiras LED / neon flex
    "tiras_led": {
        "aliases": ["tira", "cinta", "neon", "led strip"],
        "must_any": ["tira", "cinta", "neon", "led strip"],
        "must_not": ["sumergible ip68 piscina pentair"],  # genéricas fuera de piscina
        "accessories_any": ["fuente", "driver", "controlador", "rgb", "12v", "24v"],
    },

    # Lámparas decorativas
    "decorativa": {
        "aliases": ["decorativa", "decorar", "ambiente", "colgante", "aplique", "lineal"],
        "must_any": ["decorativa", "colgante", "aplique", "lineal", "decorativo"],
        "must_not": ["industrial", "highbay", "campana", "flood", "reflector"],
        "accessories_any": [],
    },

    # Industrial / highbay
    "industrial": {
        "aliases": ["industrial", "campana", "highbay", "nave", "bodega"],
        "must_any": ["industrial", "campana", "highbay"],
        "must_not": ["piscina", "sumergible", "ip68", "decorativa"],
        "accessories_any": [],
    },

    # Exterior (no sumergible)
    "exterior": {
        "aliases": ["exterior", "jardin", "jardín", "fachada", "poste", "estadio", "cancha"],
        "must_any": ["exterior", "jardin", "jardín", "ip65", "ip66", "ip67"],
        "must_not": ["piscina", "sumergible", "ip68"],
        "accessories_any": [],
    },

    # Portalámparas / bombillería
    "gu10": {
        "aliases": ["gu10"],
        "must_any": ["gu10"],
        "must_not": [],
        "accessories_any": [],
    },
    "e27": {
        "aliases": ["e27", "filamento", "vintage"],
        "must_any": ["e27"],
        "must_not": [],
        "accessories_any": [],
    },

    # Emergencia
    "emergencia": {
        "aliases": ["emergencia", "señalización", "exit"],
        "must_any": ["emergencia", "señalización", "exit"],
        "must_not": ["piscina", "sumergible"],
        "accessories_any": [],
    },
}
