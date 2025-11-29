# DOMAIN MAP — TRAFFIC LAW
# Version: 0.1 (draft)

domain_id: traffic_law
label_cs: Dopravní právo

description_domain_cs: >
  Oblast práva upravující povinnosti řidičů, provozovatelů vozidel,
  správní delikty v dopravě, přestupky řidičů, kontrolu ze strany policie,
  technický stav vozidel, bodový systém a související sankce.

# ------------------------------------------------------
# SUBDOMAINS
# ------------------------------------------------------

subdomains:
  - subdomain_id: speeding
    label_cs: Překročení rychlosti
    description_subdomain_cs: >
      Přestupky spojené s překročením rychlosti, měření rychlosti
      (radar, laser), fotodokumentace, správní řízení, pokuty a body.

  - subdomain_id: alcohol_drugs
    label_cs: Alkohol a návykové látky
    description_subdomain_cs: >
      Dechové zkoušky, krevní testy, odmítnutí testu, sankce,
      trestné činy pod vlivem, správní řízení.

  - subdomain_id: police_interaction
    label_cs: Kontrola řidiče a policie
    description_subdomain_cs: >
      Práva a povinnosti při dopravní kontrole, legitimace,
      zajištění vozidla, výzvy policie, postupy policie.

  - subdomain_id: traffic_accidents
    label_cs: Dopravní nehody
    description_subdomain_cs: >
      Postup při nehodě, oznámení policii, záznam o nehodě,
      odpovědnost, náhrada škody, správní řízení.

  - subdomain_id: vehicle_technical
    label_cs: Technický stav a STK/ME
    description_subdomain_cs: >
      Technické závady, kontrola technického stavu, STK,
      měření emisí, zákazy jízdy kvůli technickému stavu.

  - subdomain_id: administrative_offenses
    label_cs: Ostatní dopravní přestupky
    description_subdomain_cs: >
      Nesprávné parkování, pásy, telefonování, nedání přednosti,
      jízda na červenou a další přestupky.

# ------------------------------------------------------
# SITUATION KEYWORDS (Seed)
# ------------------------------------------------------

situation_keywords:

  speeding:
    - radar
    - laser
    - měření rychlosti
    - fotka z radaru
    - výzva k podání vysvětlení
    - bloková pokuta

  alcohol_drugs:
    - dechová zkouška
    - krevní test
    - odmítnutí testu
    - orientační test
    - přístroj Dräger

  police_interaction:
    - dopravní kontrola
    - policie mě zastavila
    - chtěli legitimaci
    - příkaz policisty
    - zajištění vozidla

  traffic_accidents:
    - dopravní nehoda
    - protokol o nehodě
    - viník nehody
    - pojišťovna
    - hmotná škoda

  vehicle_technical:
    - technický stav
    - závady
    - STK
    - emisní kontrola

  administrative_offenses:
    - parkování
    - pásy
    - telefonování
    - červená

# ------------------------------------------------------
# NOTES
# ------------------------------------------------------

notes:
  - Domain map definuje pouze kostru; nevytváří konkrétní intents.
  - Keywords v subdoménách slouží jako seed pro generaci konkrétních modelových situací.
  - Po schválení Domain Map vznikne Subdomain Situation Map
    → a teprve z ní budeme generovat jednotlivé intents.
  - Domain map je trvalý dokument, ze kterého bude generátor čerpat.