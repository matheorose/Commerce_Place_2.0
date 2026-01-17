# python
from typing import List, Dict, Any

CATEGORIES: List[Dict[str, Any]] = [
    # -----------------------------
    # FOOD / BOISSON
    # -----------------------------
    {
        "label": "boulangerie",
        "key": "bakery",
        "selector": {"type": "shop", "value": "bakery"},
        "synonyms": ["boulangerie", "boulangeries", "pain", "patisserie", "pâtisserie"],
    },
    {
        "label": "boucherie",
        "key": "butcher",
        "selector": {"type": "shop", "value": "butcher"},
        "synonyms": ["boucherie", "boucheries", "viande", "charcuterie"],
    },
    {
        "label": "poissonnerie",
        "key": "seafood",
        "selector": {"type": "shop", "value": "seafood"},
        "synonyms": ["poissonnerie", "poisson", "fruits de mer"],
    },
    {
        "label": "fromagerie",
        "key": "cheese",
        "selector": {"type": "shop", "value": "cheese"},
        "synonyms": ["fromagerie", "fromage", "crémerie"],
    },
    {
        "label": "épicerie",
        "key": "convenience",
        "selector": {"type": "shop", "value": "convenience"},
        "synonyms": ["épicerie", "épiceries", "epicerie", "supérette", "superette", "petit magasin"],
    },
    {
        "label": "supermarché",
        "key": "supermarket",
        "selector": {"type": "shop", "value": "supermarket"},
        "synonyms": ["supermarché", "supermarche", "hypermarché", "hypermarche", "grande surface"],
    },
    {
        "label": "primeur",
        "key": "greengrocer",
        "selector": {"type": "shop", "value": "greengrocer"},
        "synonyms": ["primeur", "fruits", "légumes", "legumes", "fruits et légumes"],
    },
    {
        "label": "caviste",
        "key": "wine_shop",
        "selector": {"type": "shop", "value": "wine"},
        "synonyms": ["caviste", "vin", "cave à vin", "cave a vin"],
    },
    {
        "label": "magasin bio",
        "key": "organic_shop",
        "selector": {"type": "shop", "value": "organic"},
        "synonyms": ["bio", "magasin bio", "produits bio", "organic"],
    },
    {
        "label": "restaurant",
        "key": "restaurant",
        "selector": {"type": "amenity", "value": "restaurant"},
        "synonyms": ["restaurant", "resto", "brasserie", "cantine"],
    },
    {
        "label": "fast-food",
        "key": "fast_food",
        "selector": {"type": "amenity", "value": "fast_food"},
        "synonyms": ["fast-food", "fast food", "kebab", "burger", "tacos"],
    },
    {
        "label": "café",
        "key": "cafe",
        "selector": {"type": "amenity", "value": "cafe"},
        "synonyms": ["café", "cafe", "coffee", "coffee shop", "salon de café"],
    },
    {
        "label": "bar",
        "key": "bar",
        "selector": {"type": "amenity", "value": "bar"},
        "synonyms": ["bar", "pub", "bistrot"],
    },
    {
        "label": "glacier",
        "key": "ice_cream",
        "selector": {"type": "shop", "value": "ice_cream"},
        "synonyms": ["glacier", "glace", "ice cream"],
    },

    # -----------------------------
    # SANTÉ
    # -----------------------------
    {
        "label": "pharmacie",
        "key": "pharmacy",
        "selector": {"type": "amenity", "value": "pharmacy"},
        "synonyms": ["pharmacie", "pharmacies", "para", "parapharmacie"],
    },
    {
        "label": "hôpital",
        "key": "hospital",
        "selector": {"type": "amenity", "value": "hospital"},
        "synonyms": ["hôpital", "hopitaux", "hopital", "chu", "clinique (grande)", "centre hospitalier"],
    },
    {
        "label": "clinique",
        "key": "clinic",
        "selector": {"type": "amenity", "value": "clinic"},
        "synonyms": ["clinique", "centre médical", "centre medical"],
    },
    {
        "label": "médecin",
        "key": "doctors",
        "selector": {"type": "amenity", "value": "doctors"},
        "synonyms": ["médecin", "medecin", "docteur", "cabinet médical", "cabinet medical", "généraliste"],
    },
    {
        "label": "dentiste",
        "key": "dentist",
        "selector": {"type": "amenity", "value": "dentist"},
        "synonyms": ["dentiste", "dentistes", "orthodontiste"],
    },
    {
        "label": "opticien",
        "key": "optician",
        "selector": {"type": "shop", "value": "optician"},
        "synonyms": ["opticien", "lunettes", "optique"],
    },
    {
        "label": "vétérinaire",
        "key": "veterinary",
        "selector": {"type": "amenity", "value": "veterinary"},
        "synonyms": ["vétérinaire", "veterinaire", "clinique vétérinaire"],
    },
    {
        "label": "laboratoire d'analyses",
        "key": "laboratory",
        "selector": {"type": "amenity", "value": "laboratory"},
        "synonyms": ["laboratoire", "analyses", "prise de sang", "labo"],
    },
    {
        "label": "hôpital vétérinaire",
        "key": "animal_hospital",
        "selector": {"type": "amenity", "value": "animal_hospital"},
        "synonyms": ["hopital veterinaire", "hôpital vétérinaire"],
    },

    # -----------------------------
    # FINANCE / ADMIN / SERVICES
    # -----------------------------
    {
        "label": "banque",
        "key": "bank",
        "selector": {"type": "amenity", "value": "bank"},
        "synonyms": ["banque", "agence bancaire", "bancaire"],
    },
    {
        "label": "distributeur (ATM)",
        "key": "atm",
        "selector": {"type": "amenity", "value": "atm"},
        "synonyms": ["dab", "atm", "distributeur", "retrait"],
    },
    {
        "label": "bureau de poste",
        "key": "post_office",
        "selector": {"type": "amenity", "value": "post_office"},
        "synonyms": ["poste", "bureau de poste", "la poste"],
    },
    {
        "label": "police",
        "key": "police",
        "selector": {"type": "amenity", "value": "police"},
        "synonyms": ["police", "commissariat"],
    },
    {
        "label": "gendarmerie",
        "key": "gendarmerie",
        "selector": {"type": "amenity", "value": "gendarmerie"},
        "synonyms": ["gendarmerie", "brigade"],
    },
    {
        "label": "mairie",
        "key": "townhall",
        "selector": {"type": "amenity", "value": "townhall"},
        "synonyms": ["mairie", "hôtel de ville", "hotel de ville"],
    },
    {
        "label": "tribunal",
        "key": "courthouse",
        "selector": {"type": "amenity", "value": "courthouse"},
        "synonyms": ["tribunal", "palais de justice"],
    },
    {
        "label": "bibliothèque",
        "key": "library",
        "selector": {"type": "amenity", "value": "library"},
        "synonyms": ["bibliothèque", "bibliotheque", "médiathèque", "mediatheque"],
    },
    {
        "label": "coworking",
        "key": "coworking_space",
        "selector": {"type": "amenity", "value": "coworking_space"},
        "synonyms": ["coworking", "espace de coworking"],
    },
    {
        "label": "agence immobilière",
        "key": "estate_agent",
        "selector": {"type": "shop", "value": "estate_agent"},
        "synonyms": ["agence immobilière", "immobilier", "estate agent"],
    },
    {
        "label": "bureau de change",
        "key": "bureau_de_change",
        "selector": {"type": "amenity", "value": "bureau_de_change"},
        "synonyms": ["bureau de change", "change", "devises"],
    },
    {
        "label": "assurance",
        "key": "insurance",
        "selector": {"type": "office", "value": "insurance"},
        "synonyms": ["assurance", "assureur"],
    },
    {
        "label": "avocat",
        "key": "lawyer",
        "selector": {"type": "office", "value": "lawyer"},
        "synonyms": ["avocat", "cabinet d'avocat", "cabinet avocat"],
    },
    {
        "label": "notaire",
        "key": "notary",
        "selector": {"type": "office", "value": "notary"},
        "synonyms": ["notaire", "étude notariale", "etude notariale"],
    },
    {
        "label": "agence de voyage",
        "key": "travel_agency",
        "selector": {"type": "shop", "value": "travel_agency"},
        "synonyms": ["agence de voyage", "voyages", "travel"],
    },

    # -----------------------------
    # TRANSPORT / MOBILITÉ
    # -----------------------------
    {
        "label": "station-service",
        "key": "fuel",
        "selector": {"type": "amenity", "value": "fuel"},
        "synonyms": ["station-service", "essence", "station essence", "carburant", "pompe"],
    },
    {
        "label": "borne de recharge",
        "key": "charging_station",
        "selector": {"type": "amenity", "value": "charging_station"},
        "synonyms": ["borne électrique", "borne electrique", "recharge", "charging"],
    },
    {
        "label": "parking",
        "key": "parking",
        "selector": {"type": "amenity", "value": "parking"},
        "synonyms": ["parking", "stationnement"],
    },
    {
        "label": "arrêt de bus",
        "key": "bus_stop",
        "selector": {"type": "highway", "value": "bus_stop"},
        "synonyms": ["arrêt de bus", "arret de bus", "bus"],
    },
    {
        "label": "gare",
        "key": "train_station",
        "selector": {"type": "railway", "value": "station"},
        "synonyms": ["gare", "station", "gare sncf"],
    },
    {
        "label": "station vélo",
        "key": "bicycle_rental",
        "selector": {"type": "amenity", "value": "bicycle_rental"},
        "synonyms": ["vélo", "velo", "vélos", "location vélo", "bicycle rental"],
    },
    {
        "label": "location de voiture",
        "key": "car_rental",
        "selector": {"type": "amenity", "value": "car_rental"},
        "synonyms": ["location voiture", "car rental", "loueur"],
    },
    {
        "label": "taxi",
        "key": "taxi",
        "selector": {"type": "amenity", "value": "taxi"},
        "synonyms": ["taxi", "station taxi"],
    },

    # -----------------------------
    # COMMERCES GÉNÉRAUX
    # -----------------------------
    {
        "label": "magasin de vêtements",
        "key": "clothes",
        "selector": {"type": "shop", "value": "clothes"},
        "synonyms": ["vêtements", "vetements", "habits", "fringues", "clothes"],
    },
    {
        "label": "chaussures",
        "key": "shoes",
        "selector": {"type": "shop", "value": "shoes"},
        "synonyms": ["chaussures", "shoe", "baskets"],
    },
    {
        "label": "bijouterie",
        "key": "jewelry",
        "selector": {"type": "shop", "value": "jewelry"},
        "synonyms": ["bijouterie", "bijoux", "joaillerie"],
    },
    {
        "label": "librairie",
        "key": "books",
        "selector": {"type": "shop", "value": "books"},
        "synonyms": ["librairie", "livres", "bouquins"],
    },
    {
        "label": "fleuriste",
        "key": "florist",
        "selector": {"type": "shop", "value": "florist"},
        "synonyms": ["fleuriste", "fleurs"],
    },
    {
        "label": "magasin de sport",
        "key": "sports",
        "selector": {"type": "shop", "value": "sports"},
        "synonyms": ["sport", "magasin de sport", "equipement sportif"],
    },
    {
        "label": "informatique",
        "key": "computer",
        "selector": {"type": "shop", "value": "computer"},
        "synonyms": ["informatique", "ordinateur", "pc", "computer shop"],
    },
    {
        "label": "téléphonie",
        "key": "mobile_phone",
        "selector": {"type": "shop", "value": "mobile_phone"},
        "synonyms": ["téléphonie", "telephone", "smartphone", "mobile"],
    },
    {
        "label": "électroménager",
        "key": "electronics",
        "selector": {"type": "shop", "value": "electronics"},
        "synonyms": ["électronique", "electronique", "électroménager", "electromenager", "high-tech"],
    },
    {
        "label": "droguerie / quincaillerie",
        "key": "hardware",
        "selector": {"type": "shop", "value": "hardware"},
        "synonyms": ["quincaillerie", "droguerie", "bricolage"],
    },
    {
        "label": "magasin de bricolage",
        "key": "doityourself",
        "selector": {"type": "shop", "value": "doityourself"},
        "synonyms": ["bricolage", "diy", "outillage", "do it yourself"],
    },
    {
        "label": "meubles",
        "key": "furniture",
        "selector": {"type": "shop", "value": "furniture"},
        "synonyms": ["meubles", "mobilier", "furniture"],
    },
    {
        "label": "animalerie",
        "key": "pet",
        "selector": {"type": "shop", "value": "pet"},
        "synonyms": ["animalerie", "animaux", "petshop", "croquettes"],
    },
    {
        "label": "coiffeur",
        "key": "hairdresser",
        "selector": {"type": "shop", "value": "hairdresser"},
        "synonyms": ["coiffeur", "coiffeuse", "salon de coiffure"],
    },
    {
        "label": "institut de beauté",
        "key": "beauty",
        "selector": {"type": "shop", "value": "beauty"},
        "synonyms": ["institut", "beauté", "beauty", "esthétique", "esthetique"],
    },
    {
        "label": "pressing",
        "key": "dry_cleaning",
        "selector": {"type": "shop", "value": "dry_cleaning"},
        "synonyms": ["pressing", "nettoyage à sec", "nettoyage a sec"],
    },
    {
        "label": "laverie",
        "key": "laundry",
        "selector": {"type": "shop", "value": "laundry"},
        "synonyms": ["laverie", "laveries", "lavomatique", "laundry"],
    },
    {
        "label": "tabac / presse",
        "key": "tobacco",
        "selector": {"type": "shop", "value": "tobacco"},
        "synonyms": ["tabac", "bureau de tabac", "presse", "journaux"],
    },
    {
        "label": "magasin de vélos",
        "key": "bicycle",
        "selector": {"type": "shop", "value": "bicycle"},
        "synonyms": ["vélo", "velo", "magasin vélo", "réparation vélo", "bicycle shop"],
    },

    # -----------------------------
    # HÉBERGEMENT / TOURISME
    # -----------------------------
    {
        "label": "hôtel",
        "key": "hotel",
        "selector": {"type": "tourism", "value": "hotel"},
        "synonyms": ["hôtel", "hotel"],
    },
    {
        "label": "auberge de jeunesse",
        "key": "hostel",
        "selector": {"type": "tourism", "value": "hostel"},
        "synonyms": ["auberge", "hostel", "jeunesse"],
    },
    {
        "label": "camping",
        "key": "camp_site",
        "selector": {"type": "tourism", "value": "camp_site"},
        "synonyms": ["camping", "camp site"],
    },
    {
        "label": "musée",
        "key": "museum",
        "selector": {"type": "tourism", "value": "museum"},
        "synonyms": ["musée", "musee"],
    },
    {
        "label": "office de tourisme",
        "key": "tourism_information",
        "selector": {"type": "tourism", "value": "information"},
        "synonyms": ["office de tourisme", "info tourisme", "tourist info"],
    },
    {
        "label": "attraction",
        "key": "attraction",
        "selector": {"type": "tourism", "value": "attraction"},
        "synonyms": ["attraction", "site touristique", "monument"],
    },

    # -----------------------------
    # LOISIRS / SPORTS / CULTURE
    # -----------------------------
    {
        "label": "cinéma",
        "key": "cinema",
        "selector": {"type": "amenity", "value": "cinema"},
        "synonyms": ["cinéma", "cinema"],
    },
    {
        "label": "théâtre",
        "key": "theatre",
        "selector": {"type": "amenity", "value": "theatre"},
        "synonyms": ["théâtre", "theatre"],
    },
    {
        "label": "salle de sport",
        "key": "fitness_centre",
        "selector": {"type": "leisure", "value": "fitness_centre"},
        "synonyms": ["salle de sport", "fitness", "gym"],
    },
    {
        "label": "stade",
        "key": "sports_centre",
        "selector": {"type": "leisure", "value": "sports_centre"},
        "synonyms": ["stade", "complexe sportif", "sports centre"],
    },
    {
        "label": "piscine",
        "key": "swimming_pool",
        "selector": {"type": "leisure", "value": "swimming_pool"},
        "synonyms": ["piscine", "swimming pool"],
    },
    {
        "label": "parc",
        "key": "park",
        "selector": {"type": "leisure", "value": "park"},
        "synonyms": ["parc", "jardin"],
    },
    {
        "label": "aire de jeux",
        "key": "playground",
        "selector": {"type": "leisure", "value": "playground"},
        "synonyms": ["aire de jeux", "jeux enfants", "playground"],
    },

    # -----------------------------
    # ÉDUCATION
    # -----------------------------
    {
        "label": "école",
        "key": "school",
        "selector": {"type": "amenity", "value": "school"},
        "synonyms": ["école", "ecole", "primaire", "élémentaire", "elementaire"],
    },
    {
        "label": "collège",
        "key": "college",
        "selector": {"type": "amenity", "value": "school"},
        "synonyms": ["collège", "college"],
    },
    {
        "label": "lycée",
        "key": "high_school",
        "selector": {"type": "amenity", "value": "school"},
        "synonyms": ["lycée", "lycee"],
    },
    {
        "label": "université",
        "key": "university",
        "selector": {"type": "amenity", "value": "university"},
        "synonyms": ["université", "universite", "fac", "campus"],
    },

    # -----------------------------
    # ARTISANS / SERVICES TECHNIQUES
    # -----------------------------
    {
        "label": "garage auto",
        "key": "car_repair",
        "selector": {"type": "shop", "value": "car_repair"},
        "synonyms": ["garage", "réparation auto", "reparation auto", "mécanicien", "mecanicien"],
    },
    {
        "label": "carrosserie",
        "key": "bodywork",
        "selector": {"type": "shop", "value": "car_repair"},
        "synonyms": ["carrosserie", "carrossier"],
    },
    {
        "label": "plombier",
        "key": "plumber",
        "selector": {"type": "craft", "value": "plumber"},
        "synonyms": ["plombier", "plomberie"],
    },
    {
        "label": "électricien",
        "key": "electrician",
        "selector": {"type": "craft", "value": "electrician"},
        "synonyms": ["électricien", "electricien", "électricité", "electricite"],
    },
    {
        "label": "menuisier",
        "key": "carpenter",
        "selector": {"type": "craft", "value": "carpenter"},
        "synonyms": ["menuisier", "charpentier", "carpenter"],
    },
    {
        "label": "serrurier",
        "key": "locksmith",
        "selector": {"type": "craft", "value": "locksmith"},
        "synonyms": ["serrurier", "clés", "cles", "locksmith"],
    },
    {
        "label": "cordonnier",
        "key": "shoemaker",
        "selector": {"type": "craft", "value": "shoemaker"},
        "synonyms": ["cordonnier", "réparation chaussures", "reparation chaussures"],
    },

    # -----------------------------
    # DIVERS UTILES
    # -----------------------------
    {
        "label": "toilettes publiques",
        "key": "toilets",
        "selector": {"type": "amenity", "value": "toilets"},
        "synonyms": ["toilettes", "wc", "toilettes publiques"],
    },
    {
        "label": "eau potable",
        "key": "drinking_water",
        "selector": {"type": "amenity", "value": "drinking_water"},
        "synonyms": ["eau", "fontaine", "eau potable", "drinking water"],
    },
    {
        "label": "recyclage",
        "key": "recycling",
        "selector": {"type": "amenity", "value": "recycling"},
        "synonyms": ["recyclage", "tri", "conteneur verre", "déchetterie (souvent amenity=waste_disposal)"],
    },
    {
        "label": "déchetterie / dépôt déchets",
        "key": "waste_disposal",
        "selector": {"type": "amenity", "value": "waste_disposal"},
        "synonyms": ["déchetterie", "dechetterie", "dépôt déchets", "depot dechets"],
    },
]
