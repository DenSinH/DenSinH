from generic import *

import json
import requests


# obtained from https://twistedvoxel.com/elden-ring-all-trophies-and-achievements-guide/
achievements = {
    'Age of the Stars': 'Achieved the "Age of the Stars" ending',
    'Ancestor Spirit': 'Defeated Ancestor Spirit',
    'Astel, Naturalborn of the Void': 'Defeated Astel, Naturalborn of the Void',
    'Commander Niall': 'Defeated Commander Niall',
    'Dragonkin Soldier of Nokstella': 'Defeated Dragonkin Soldier of Nokstella',
    'Dragonlord Placidusax': 'Defeated Dragonlord Placidusax',
    'Elden Lord': 'Achieved the "Elden Lord" ending',
    'Elden Ring': 'Obtained all trophies',
    'Elemer of the Briar': 'Defeated Elemer of the Briar',
    'Erdtree Aflame': 'Used kindling to set the Erdtree aflame',
    'Fire Giant': 'Defeated Fire Giant',
    'God-Slaying Armament': 'Upgraded any armament to its highest stage',       
    'Godfrey, the First Lord': 'Defeated Godfrey the First Lord',
    'Godskin Duo': 'Defeated Goskin Duo',
    'Godskin Noble': 'Defeated Goskin Noble',
    'Great Rune': 'Restored the power of a Great Rune',
    'Hoarah Loux the Warrior': 'Defeated Hoarah Loux the Warrior',
    'Legendary Armaments': 'Acquired all legendary armaments',
    'Legendary Ashen Remains': 'Acquired all legendary ashen remains',
    'Legendary Sorceries and Incantations': 'Acquired all legendary sorceries and '
                                            'incantations',
    'Legendary Talismans': 'Acquired all legendary talismans',
    'Leonine Misbegotten': 'Defeated the Leonine Misbegotten',
    'Lichdragon Fortissax': 'Defeated Lichdragon Fortissax',
    'Lord of Frenzied Flame': 'Achieved the "Lord of the Frenzied Flame" ending',
    'Loretta, Knight of the Haligtree': 'Defeated Loretta, Knight of the '
                                        'Haligtree',
    'Magma Wyrm Makar': 'Defeated Magma Wyrm Makar',
    'Maliketh, the Black Blade': 'DefeatedShardbearer Maliketh, the Black Blade',
    'Margit, the Fell Omen': 'Defeated Margit, the Fell Omen',
    'Mimic Tear': 'Defeated Mimic Tear',
    'Mohg, the Omen': 'Defeated Mohg, the Omen',
    'Red Wolf of Radagon': 'Defeated the Red Wolf of Radagon',
    'Regal Ancestor Spirit': 'Defeated Regal Ancestor Spirit',
    'Rennala, Queen of the Full Moon': 'Defeated Rennala, Queen of the Full Moon',
    'Roundtable Hold': 'Arrived at Roundtable Hold',
    'Royal Knight Loretta': 'Defeated Royal Knight Loretta',
    'Shardbearer Godrick': 'Defeated Shardbearer Godrick',
    'Shardbearer Melania': 'Defeated Shardbearer Malenia',
    'Shardbearer Mohg': 'Defeated Shardbearer Mohg',
    'Shardbearer Morgott': 'Defeated Shardbearer Morgott',
    'Shardbearer Radahn': 'Defeated Shardbearer Radahn',
    'Shardbearer Rykard': 'Defeated Shardbearer Rykard',
    'Valiant Gargoyle': 'Defeated Valiant Gargoyle'
 }

# obtained from https://eldenring.wiki.fextralife.com/Trophy+&+Achievement+Guide
LEGENDARIES = {
    'armaments': {
        'Ruins Greatsword': 'Defeat the Misbegotten Warrior and Crucible Knight in Redmane Castle',
        'Eclipse Shotel': 'Chest in Castle Sol',
        'Grafted Blade Greatsword': 'Kill Leonine Misbegotten in Castle Morne',
        'Sword of Night and Flame': 'Chest in the Carian Manor',
        'Marais Executioner\'s Sword': 'Kill Elemer of the Briar in The Shaded Castle',
        'Dark Moon Greatsword': 'Follow Ranni\'s quest until the Moonlight Altar',
        'Devourer\'s Scepter': 'Kill Invader Bernahl in Farum Azula',
        'Golden Order Greatsword': 'Kill Misbegotten Crusader in the Cave of the Forlorn',
        'Bolt of Gransax': 'Loot on the Giant spear in Leyndell',
    },
    'ashen remains': {
        'Lhutel the Headless': 'Dropped by the Cemetery Shade at the Tombsward Catacombs',
        'Black Knife Tiche': 'Dropped by Alecto, Black Knife Ringleader upon defeat at the Ringleader\'s Evergaol',
        'Redmane Knight Ogha Ashes': 'Dropped by Putrid Tree Spirit in the War Dead Catacombs',
        'Mimic Tear': 'Found in a chest locked behind an imp statue door in Night\'s Sacred Ground',
        'Ancient Dragon Knight Kristoff Ashes': 'Can be found in Sainted Hero\'s Grave west of Leyndell, the Royal Capital',
        'Cleanrot Knight Finlay Ashes': 'Found in a chest protected by a knight in Elphael, Brace of the Haligtree',
    },
    'sorceries and incantations': {
        'Flame of the Fell God': 'Dropped by Adan, Thief of Fire upon defeat',
        'Greyoll\'s Roar': 'Can be purchased at the Cathedral of Dragon Communion for a Dragon Heart after defeating Greyoll',
        'Elden Stars': 'Can be found near the Great Waterfall Crest Site of Grace',
        'Founding Rain of Stars': 'Inside a chest within Heretical Rise, in Mountaintops of the Giants',
        'Ranni\'s Dark Moon': 'Found in a chest at the top of the tower at Chelona\'s Rise',
        'Comet Azur': ' Acquired from Primeval Sorcerer Azur sitting near the cliffs in the northeast of Hermit Village in Mt. Gelmir',
        'Stars of Ruin': 'Given by Master Lusat when interacted with inside the Sellia Hideaway in Caelid',
    },
    'talismans': {
        'Radagon Icon': 'Found inside a treasure chest on the second floor of the Debate Parlor Site of Grace',
        'Radagon\'s Soreseal': 'Found on a corpse in Fort Faroth',
        'Godfrey Icon': 'Drops from Godefroy the Grafted in the Golden Lineage Evergaol',
        'Moon of Nokstella': 'Found in a chest underneath a massive throne in Nokstella, Eternal City',
        'Dragoncrest Greatshield Talisman': 'Found in a chest near the Drainage Channel Site of Grace.',
        'Marika\'s Soreseal': 'Found on an altar in a room requiring a Stonesword Key in Elphael, Brace of the Haligtree',
        'Old Lord\'s Talisman': 'Found in a chest in Crumbling Farum Azula',
        'Erdtree\'s Favor +2': 'Found on a dead tree in Leyndell, Ashen Capital (endgame/post-game)',
    }
}

achievement_data = {}


def url_exists(url):
    try:
        response = requests.head(url)
        return response.status_code < 400
    except:
        print(f"Could not fetch wiki link: {url}")
        return False


for achievement, how_to_unlock in achievements.items():
    achievement_data[achievement] = { "how-to-unlock": how_to_unlock }

    type = MISC
    url = None
    sub = None
    if "ending" in how_to_unlock.lower():
        type = ENDING
        url = "https://eldenring.wiki.fextralife.com/Endings"
    elif "defeated" in how_to_unlock.lower():
        type = BOSS
        page_name = achievement.replace(" ", "+")
        url = f"https://eldenring.wiki.fextralife.com/{page_name}"
    elif "legendary" in how_to_unlock.lower():
        type = LEGENDARY_ITEMS
        sub = {
            item: {"where": where} for item, where in LEGENDARIES[achievement.replace("Legendary ", "").lower()].items()
        }


    if url is not None:
        if not url_exists(url):
            url = None

    if sub is not None:
        for item, data in sub.items():
            page_name = item.strip("+1234567890 ").replace(" ", "+")
            sub_url = f"https://eldenring.wiki.fextralife.com/{page_name}"
            if not url_exists(sub_url):
                sub_url = None
            data["url"] = sub_url

    achievement_data[achievement]["type"] = type
    achievement_data[achievement]["url"] = url
    achievement_data[achievement]["sub"] = sub

# some links aren't picked up
achievement_data["Hoarah Loux the Warrior"]["url"] = "https://eldenring.wiki.fextralife.com/Godfrey,+First+Elden+Lord"
achievement_data["Shardbearer Godrick"]["url"] = "https://eldenring.wiki.fextralife.com/Godrick+the+Grafted"
achievement_data["Shardbearer Melania"]["url"] = "https://eldenring.wiki.fextralife.com/Malenia+Blade+of+Miquella"
achievement_data["Shardbearer Mohg"]["url"] = "https://eldenring.wiki.fextralife.com/Mohg,+Lord+of+Blood"
achievement_data["Shardbearer Morgott"]["url"] = "https://eldenring.wiki.fextralife.com/Morgott+the+Omen+King"
achievement_data["Shardbearer Radahn"]["url"] = "https://eldenring.wiki.fextralife.com/Starscourge+Radahn"
achievement_data["Shardbearer Rykard"]["url"] = "https://eldenring.wiki.fextralife.com/Rykard,+Lord+of+Blasphemy"


with open("./achievements.json", "w+") as f:
    json.dump(achievement_data, f, indent=4)