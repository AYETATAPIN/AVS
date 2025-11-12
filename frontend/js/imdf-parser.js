// IMDF Parser
class IMDFParser {
    constructor() {
        this.buildings = new Map();
        this.addresses = new Map();
        this.units = new Map();
        this.levels = new Map();
    }

    parseBuildings(geojsonData) {
        if (!geojsonData?.features) return;
        
        geojsonData.features.forEach(feature => {
            if (feature.feature_type === 'building') {
                this.buildings.set(feature.id, {
                    id: feature.id,
                    name: feature.properties.name,
                    address_id: feature.properties.address_id
                });
            }
        });
    }

    parseAddresses(geojsonData) {
        if (!geojsonData?.features) return;
        
        geojsonData.features.forEach(feature => {
            if (feature.feature_type === 'address') {
                this.addresses.set(feature.id, {
                    id: feature.id,
                    address: feature.properties.address,
                    locality: feature.properties.locality
                });
            }
        });
    }

    parseUnits(geojsonData) {
        if (!geojsonData?.features) return;
        
        geojsonData.features.forEach(feature => {
            if (feature.feature_type === 'unit') {
                let name = null;
                if (feature.properties.name) {
                    name = typeof feature.properties.name === 'object' 
                        ? feature.properties.name.ru 
                        : feature.properties.name;
                }
                
                this.units.set(feature.id, {
                    id: feature.id,
                    level_id: feature.properties.level_id,
                    name: name
                });
            }
        });
    }

    parseLevels(geojsonData) {
        if (!geojsonData?.features) return;
        
        geojsonData.features.forEach(feature => {
            if (feature.feature_type === 'level') {
                const buildingIds = feature.properties.building_ids || [];
                this.levels.set(feature.id, {
                    id: feature.id,
                    name: feature.properties.name,
                    building_id: buildingIds[0] || null,
                    ordinal: feature.properties.ordinal
                });
            }
        });
    }

    getAllClassrooms() {
        const classrooms = [];
        
        for (const [unitId, unit] of this.units) {
            if (!unit.name) continue;

            const level = this.levels.get(unit.level_id);
            if (!level) continue;

            let building = null;
            let address = null;

            if (level.building_id) {
                building = this.buildings.get(level.building_id);
                if (building?.address_id) {
                    address = this.addresses.get(building.address_id);
                }
            }
            
            classrooms.push({
                id: unitId,
                name: this.getRoomName(unit),
                roomNumber: this.getRoomNumber(unit), // Добавляем номер комнаты
                buildingName: building ? (building.name?.ru || 'Неизвестное здание') : 'Неизвестный корпус',
                addressText: address ? `${address.address}, ${address.locality}` : null,
                floor: this.getFloorDisplay(level.ordinal),
                building: building
            });
        }
        
        classrooms.sort((a, b) => {
            const numA = a.name.match(/\d+/);
            const numB = b.name.match(/\d+/);
            return numA && numB ? parseInt(numA[0]) - parseInt(numB[0]) : a.name.localeCompare(b.name, 'ru');
        });
        
        return classrooms;
    }

    getRoomName(unit) {
        if (!unit.name) return `Помещение ${unit.id.slice(0, 8)}`;
        return /^\d+$/.test(unit.name) ? `Аудитория ${unit.name}` : unit.name;
    }

    getRoomNumber(unit) {
        if (!unit.name) return null;
        const name = typeof unit.name === 'object' ? unit.name.ru : unit.name;
        return name.toString().trim();
    }

    getFloorDisplay(ordinal) {
        if (ordinal === -1) return 'Цокольный';
        if (ordinal === 0) return '1';
        if (ordinal === 1) return '2';
        return ordinal?.toString() || '?';
    }

    getAllBuildings() {
        const buildings = [];
        for (const [id, building] of this.buildings) {
            if (building.address_id) {
                building.address = this.addresses.get(building.address_id);
            }
            buildings.push(building);
        }
        return buildings;
    }
}

// Загрузка GeoJSON файлов
async function loadGeoJSONFile(filePath) {
    try {
        const response = await fetch(filePath);
        return response.ok ? await response.json() : null;
    } catch (error) {
        console.warn(`Не удалось загрузить ${filePath}`);
        return null;
    }
}

// Инициализация IMDF данных
async function initializeIMDFData() {
    const parser = new IMDFParser();
    
    try {
        console.log('Загружаем IMDF данные из файлов...');
        const [addressData, buildingData, levelData, unitData] = await Promise.all([
            loadGeoJSONFile('./imdf-data/address.geojson'),
            loadGeoJSONFile('./imdf-data/building.geojson'),
            loadGeoJSONFile('./imdf-data/level.geojson'),
            loadGeoJSONFile('./imdf-data/unit.geojson')
        ]);
        
        if (addressData) parser.parseAddresses(addressData);
        if (buildingData) parser.parseBuildings(buildingData);
        if (levelData) parser.parseLevels(levelData);
        if (unitData) parser.parseUnits(unitData);
        
        const classrooms = parser.getAllClassrooms();
        console.log(`Загружено ${classrooms.length} аудиторий`);
        
        return {
            classrooms: classrooms,
            buildings: parser.getAllBuildings()
        };
        
    } catch (error) {
        console.error('Ошибка загрузки IMDF данных:', error);
        throw error;
    }
}