import json
import gc

from utils import log_console_file


BUILDING_ALIASES = {
    "\u0410\u0443\u0434\u0438\u0442\u043e\u0440\u043d\u044b\u0439 \u043a\u043e\u0440\u043f\u0443\u0441": "Auditory",
    "\u0413\u043b\u0430\u0432\u043d\u044b\u0439 \u043a\u043e\u0440\u043f\u0443\u0441": "Main",
    "\u0423\u0447\u0435\u0431\u043d\u043e-\u043b\u0430\u0431\u043e\u0440\u0430\u0442\u043e\u0440\u043d\u044b\u0439 \u043a\u043e\u0440\u043f\u0443\u0441": "Educational_Laboratory",
    "\u0423\u0447\u0435\u0431\u043d\u044b\u0439 \u043a\u043e\u0440\u043f\u0443\u0441 \u21161": "Educational_1",
    "\u0420\u0435\u043a\u0442\u043e\u0440\u0430\u0442": "Rectorate",
    "РђСѓРґРёС‚РѕСЂРЅС‹Р№ РєРѕСЂРїСѓСЃ": "Auditory",
    "Р“Р»Р°РІРЅС‹Р№ РєРѕСЂРїСѓСЃ": "Main",
    "РЈС‡РµР±РЅРѕ-Р»Р°Р±РѕСЂР°С‚РѕСЂРЅС‹Р№ РєРѕСЂРїСѓСЃ": "Educational_Laboratory",
    "РЈС‡РµР±РЅС‹Р№ РєРѕСЂРїСѓСЃ в„–1": "Educational_1",
    "Р РµРєС‚РѕСЂР°С‚": "Rectorate",
}


ROOM_MOJIBAKE_REPLACEMENTS = {
    "р°": "\u0430",
    "р±": "\u0431",
    "рµ": "\u0435",
    "сѓ": "\u0443",
    "сЂ": "\u0440",
    "сЃ": "\u0441",
    "с‚": "\u0442",
    "с…": "\u0445",
}

ROOM_LATIN_TO_CYR = {
    "a": "\u0430",
    "b": "\u0431",
    "c": "\u0441",
    "e": "\u0435",
    "k": "\u043a",
    "m": "\u043c",
    "o": "\u043e",
    "p": "\u0440",
    "t": "\u0442",
    "x": "\u0445",
    "y": "\u0443",
}


class LocationService:
    def __init__(self, config: dict) -> None:
        self.config: dict = config
        self.mapping: object = None

    def _load_mapping(self) -> object:
        mapping_cfg = self.config.get("LOCATION_MAPPING", {})
        mapping_file = str(mapping_cfg.get("file", "location_mapping.json"))
        try:
            with open(mapping_file, "r") as file_obj:
                mapping = json.load(file_obj)
            sensors = mapping.get("sensors", {})
            if not isinstance(sensors, dict) or not sensors:
                raise ValueError("invalid sensors mapping")
            log_console_file(
                f"Location mapping loaded from {mapping_file}: {len(sensors)} sensors"
            )
            return mapping
        except Exception as err:
            log_console_file("Location mapping load failed: " + str(err))
            return None

    def _ensure_mapping_loaded(self) -> bool:
        if self.mapping is not None:
            return True
        try:
            gc.collect()
        except Exception:
            pass

        loaded = self._load_mapping()
        if loaded is None:
            self.mapping = {"sensors": {}, "buildings": {}}
            return False

        self.mapping = loaded
        return True

    def normalize_room(self, room: str) -> str:
        value = str(room or "").strip().lower().replace(" ", "")
        if not value:
            return value

        for wrong, normal in ROOM_MOJIBAKE_REPLACEMENTS.items():
            value = value.replace(wrong, normal)

        last = value[-1]
        if last in ROOM_LATIN_TO_CYR:
            value = value[:-1] + ROOM_LATIN_TO_CYR[last]
        return value

    def normalize_building(self, building: str) -> str:
        text = str(building or "").strip()
        if text in BUILDING_ALIASES:
            return BUILDING_ALIASES[text].lower()
        return text.lower()

    def building_to_code(self, building: str) -> str:
        text = str(building or "").strip()
        if text in BUILDING_ALIASES:
            return BUILDING_ALIASES[text]
        return text

    def validate_location(self, sensor_id: str, building: str, room: str) -> tuple:
        if not self._ensure_mapping_loaded():
            return False, "location mapping is unavailable (memory/file error)"

        sensors = self.mapping.get("sensors", {})
        entry = sensors.get(sensor_id)
        if entry is None:
            return False, "sensor_id not found in mapping"

        expected_room = str(entry.get("room", ""))
        if self.normalize_room(expected_room) != self.normalize_room(str(room)):
            return False, "room does not match sensor mapping"

        expected_building_code = str(entry.get("building", "")).lower()
        expected_building_ru = str(self.mapping.get("buildings", {}).get(entry.get("building", ""), "")).lower()
        expected_building_ru = self.normalize_building(expected_building_ru)
        provided_building = self.normalize_building(building)

        if provided_building not in (expected_building_code, expected_building_ru):
            return False, "building does not match sensor mapping"

        return True, "ok"
