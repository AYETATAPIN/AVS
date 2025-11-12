class IMDFParser {
    constructor() {
        this.buildings = new Map();
        this.addresses = new Map();
        this.units = new Map();
        this.levels = new Map();
    }

    // Парсинг building.geojson
    parseBuildings(geojsonData) {
        if (!geojsonData || !geojsonData.features) {
            console.error('Invalid building GeoJSON data');
            return;
        }

        geojsonData.features.forEach(feature => {
            if (feature.feature_type === 'building') {
                this.buildings.set(feature.id, {
                    id: feature.id,
                    name: feature.properties.name,
                    address_id: feature.properties.address_id,
                    category: feature.properties.category,
                    geometry: feature.geometry
                });
            }
        });
        
        console.log(`Loaded ${this.buildings.size} buildings`);
    }

    // Парсинг address.geojson  
    parseAddresses(geojsonData) {
        if (!geojsonData || !geojsonData.features) {
            console.error('Invalid address GeoJSON data');
            return;
        }

        geojsonData.features.forEach(feature => {
            if (feature.feature_type === 'address') {
                this.addresses.set(feature.id, {
                    id: feature.id,
                    address: feature.properties.address,
                    locality: feature.properties.locality,
                    postal_code: feature.properties.postal_code,
                    country: feature.properties.country
                });
            }
        });
        
        console.log(`Loaded ${this.addresses.size} addresses`);
    }

    // Парсинг unit.geojson - АДАПТИРОВАН ПОД РЕАЛЬНЫЕ ДАННЫЕ
    parseUnits(geojsonData) {
        if (!geojsonData || !geojsonData.features) {
            console.error('Invalid unit GeoJSON data');
            return;
        }

        geojsonData.features.forEach(feature => {
            if (feature.feature_type === 'unit') {
                const unitData = {
                    id: feature.id,
                    level_id: feature.properties.level_id,
                    category: feature.properties.category,
                    geometry: feature.geometry,
                    // Дополнительные свойства
                    accessibility: feature.properties.accessibility,
                    alt_name: feature.properties.alt_name,
                    restriction: feature.properties.restriction
                };

                // Обработка имени - может быть null, объектом или строкой
                if (feature.properties.name) {
                    if (typeof feature.properties.name === 'object') {
                        unitData.name = feature.properties.name;
                    } else {
                        unitData.name = { ru: feature.properties.name };
                    }
                } else {
                    unitData.name = null;
                }

                this.units.set(feature.id, unitData);
            }
        });
        
        console.log(`Loaded ${this.units.size} units/classrooms`);
        
        // Выведем примеры для отладки
        const namedUnits = Array.from(this.units.values()).filter(unit => unit.name);
        console.log('Named units examples:', namedUnits.slice(0, 5));
    }

    // Парсинг level.geojson
    parseLevels(geojsonData) {
        if (!geojsonData || !geojsonData.features) {
            console.error('Invalid level GeoJSON data');
            return;
        }

        geojsonData.features.forEach(feature => {
            if (feature.feature_type === 'level') {
                this.levels.set(feature.id, {
                    id: feature.id,
                    name: feature.properties.name,
                    building_id: feature.properties.building_id,
                    ordinal: feature.properties.ordinal, // номер этажа
                    geometry: feature.geometry
                });
            }
        });
        
        console.log(`Loaded ${this.levels.size} levels`);
    }

    // Получить все аудитории с полной информацией - ОБНОВЛЕНО
    getAllClassrooms() {
        const classrooms = [];
        
        for (const [unitId, unit] of this.units) {
            // Фильтруем только именованные помещения (аудитории с номерами)
            if (this.isClassroom(unit)) {
                const level = this.levels.get(unit.level_id);
                let building = null;
                let address = null;

                if (level && level.building_id) {
                    building = this.buildings.get(level.building_id);
                    if (building && building.address_id) {
                        address = this.addresses.get(building.address_id);
                    }
                }
                
                const roomName = this.getRoomName(unit);
                
                classrooms.push({
                    id: unitId,
                    name: roomName,
                    unit: unit,
                    building: building,
                    address: address,
                    level: level,
                    floor: level ? (level.ordinal || '?') : '?',
                    buildingName: building ? 
                        (building.name?.ru || building.name || 'Неизвестное здание') : 
                        'Неизвестный корпус',
                    addressText: address ? 
                        `${address.address}, ${address.locality}` : 
                        'Адрес не указан',
                    geometry: unit.geometry // Добавляем геометрию для карты
                });
            }
        }
        
        // Сортируем по имени аудитории
        classrooms.sort((a, b) => a.name.localeCompare(b.name, 'ru'));
        
        return classrooms;
    }

    // Определяем является ли unit аудиторией - ОБНОВЛЕНО
    isClassroom(unit) {
        // Включаем все именованные помещения (с номерами)
        if (!unit.name || !unit.name.ru) {
            return false;
        }

        const name = unit.name.ru.trim();
        
        // Игнорируем пустые имена
        if (!name || name === 'null') {
            return false;
        }

        // Включаем помещения с числовыми названиями (номера аудиторий)
        if (/^\d+$/.test(name)) {
            return true;
        }

        // Включаем помещения с названиями, содержащими ключевые слова
        const classroomKeywords = [
            'аудитория', 'ауд', 'лекционная', 'лекция', 
            'класс', 'кабинет', 'лаборатория', 'лаб'
        ];
        
        const lowerName = name.toLowerCase();
        return classroomKeywords.some(keyword => lowerName.includes(keyword));
    }

    // Получаем читаемое имя комнаты
    getRoomName(unit) {
        if (!unit.name || !unit.name.ru) {
            return `Помещение ${unit.id.slice(0, 8)}`;
        }
        
        const name = unit.name.ru.trim();
        
        // Если имя просто число - добавляем "Аудитория"
        if (/^\d+$/.test(name)) {
            return `Аудитория ${name}`;
        }
        
        return name;
    }

    // Получить здание по ID
    getBuilding(buildingId) {
        const building = this.buildings.get(buildingId);
        if (building && building.address_id) {
            building.address = this.addresses.get(building.address_id);
        }
        return building;
    }

    // Получить все здания
    getAllBuildings() {
        const buildings = [];
        for (const [id, building] of this.buildings) {
            const buildingWithAddress = this.getBuilding(id);
            buildings.push(buildingWithAddress);
        }
        return buildings;
    }

    // Статистика
    getStats() {
        const classrooms = this.getAllClassrooms();
        return {
            totalBuildings: this.buildings.size,
            totalAddresses: this.addresses.size, 
            totalUnits: this.units.size,
            totalLevels: this.levels.size,
            totalClassrooms: classrooms.length,
            namedClassrooms: classrooms.filter(c => c.name && c.name !== 'Помещение').length
        };
    }

    // Получить геоданные для карты
    getGeoJSONForMap() {
        const classrooms = this.getAllClassrooms();
        
        return {
            type: "FeatureCollection",
            features: classrooms.map(classroom => ({
                type: "Feature",
                id: classroom.id,
                properties: {
                    name: classroom.name,
                    building: classroom.buildingName,
                    floor: classroom.floor,
                    // Здесь позже добавятся реальные данные о воздухе
                    air_quality: "good", // временно
                    co2: 0, // временно
                    temperature: 0, // временно
                    humidity: 0 // временно
                },
                geometry: classroom.geometry
            }))
        };
    }
}

// Функция для загрузки GeoJSON файлов
async function loadGeoJSONFile(filePath) {
    try {
        const response = await fetch(filePath);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Error loading ${filePath}:`, error);
        return null;
    }
}

// Основная функция инициализации - ОБНОВЛЕНА
async function initializeIMDFData() {
    const parser = new IMDFParser();
    
    console.log('Loading IMDF data...');
    
    try {
        // Загружаем файлы по очереди для отладки
        const addressData = await loadGeoJSONFile('imdf-data/address.geojson');
        if (addressData) {
            parser.parseAddresses(addressData);
        } else {
            console.warn('Address data not loaded');
        }

        const buildingData = await loadGeoJSONFile('imdf-data/building.geojson');
        if (buildingData) {
            parser.parseBuildings(buildingData);
        } else {
            console.warn('Building data not loaded');
        }

        const unitData = await loadGeoJSONFile('imdf-data/unit.geojson');
        if (unitData) {
            parser.parseUnits(unitData);
        } else {
            console.warn('Unit data not loaded');
        }

        const levelData = await loadGeoJSONFile('imdf-data/level.geojson');
        if (levelData) {
            parser.parseLevels(levelData);
        } else {
            console.warn('Level data not loaded - some information will be missing');
        }
        
        // Выводим статистику
        const stats = parser.getStats();
        console.log('IMDF Data Statistics:', stats);
        
        // Получаем все аудитории
        const classrooms = parser.getAllClassrooms();
        console.log('Found classrooms:', classrooms);
        
        return {
            parser,
            classrooms,
            buildings: parser.getAllBuildings(),
            geoJSON: parser.getGeoJSONForMap(),
            stats
        };
        
    } catch (error) {
        console.error('Error in IMDF initialization:', error);
        throw error;
    }
}