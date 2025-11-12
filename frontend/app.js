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

// Сервис для работы с API датчиков
class SensorAPIService {
    constructor(baseUrl = '/api') {
        this.baseUrl = baseUrl;
    }

    async getAllSensorsData() {
        try {
            console.log('Запрос данных с сервера...');
            const response = await fetch(`${this.baseUrl}/sensors/current`);
            if (!response.ok) throw new Error(`Ошибка сервера: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('Ошибка загрузки данных с датчиков:', error);
            throw error;
        }
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

// Vue приложение
const { createApp, ref, computed, onMounted } = Vue;

createApp({
    setup() {
        const currentTime = ref(new Date().toLocaleTimeString('ru-RU'));
        const classrooms = ref([]);
        const buildings = ref([]);
        const loading = ref(true);
        const error = ref(null);
        const useDemoMode = ref(false);
        const lastUpdate = ref(null);
        const imdfData = ref(null);

        const selectedBuilding = ref("all");
        const selectedQuality = ref("all");

        const apiService = new SensorAPIService();

        // Определяем качество воздуха на основе CO2
        const calculateAirQuality = (co2) => {
            if (!co2) return null;
            if (co2 < 600) return "excellent";
            if (co2 < 800) return "good";
            if (co2 < 1000) return "fair";
            return "poor";
        };

        // Генератор демо-данных для реальных аудиторий
        const generateDemoData = (classrooms) => {
            return classrooms.map(room => {
                const baseCO2 = 400 + Math.random() * 1000;
                const co2 = Math.floor(baseCO2);
                
                return {
                    ...room,
                    co2: co2,
                    temperature: (18 + Math.random() * 10).toFixed(1),
                    humidity: Math.floor(30 + Math.random() * 50),
                    airQuality: calculateAirQuality(co2),
                    lastUpdate: new Date(),
                    hasRealData: false
                };
            });
        };

        // Объединяем данные IMDF с данными датчиков
        const mergeSensorData = (classrooms, sensorData) => {
            const sensorMap = {};
            sensorData.data?.forEach(sensor => {
                sensorMap[sensor.unit_id] = sensor;
            });

            return classrooms.map(room => {
                const sensor = sensorMap[room.id];
                
                if (sensor) {
                    return {
                        ...room,
                        co2: sensor.co2,
                        temperature: sensor.temperature,
                        humidity: sensor.humidity,
                        airQuality: calculateAirQuality(sensor.co2),
                        lastUpdate: new Date(sensor.last_update),
                        hasRealData: true
                    };
                } else {
                    return {
                        ...room,
                        co2: null,
                        temperature: null,
                        humidity: null,
                        airQuality: null,
                        lastUpdate: null,
                        hasRealData: false
                    };
                }
            });
        };

        // Загрузка реальных данных
        const loadRealData = async () => {
            try {
                console.log('Загрузка реальных данных...');
                loading.value = true;
                error.value = null;

                if (!imdfData.value) {
                    imdfData.value = await initializeIMDFData();
                }

                const sensorData = await apiService.getAllSensorsData();
                classrooms.value = mergeSensorData(imdfData.value.classrooms, sensorData);
                buildings.value = imdfData.value.buildings;
                useDemoMode.value = false;
                lastUpdate.value = new Date(sensorData.timestamp);

                console.log('Реальные данные успешно загружены');

            } catch (err) {
                console.error('Ошибка загрузки реальных данных:', err);
                error.value = 'Не удалось подключиться к серверу датчиков';
            } finally {
                loading.value = false;
            }
        };

        // Включение демо-режима
        const enableDemoMode = async () => {
            try {
                console.log('Включение демо-режима...');
                loading.value = true;
                error.value = null;

                if (!imdfData.value) {
                    imdfData.value = await initializeIMDFData();
                }

                classrooms.value = generateDemoData(imdfData.value.classrooms);
                buildings.value = imdfData.value.buildings;
                useDemoMode.value = true;
                lastUpdate.value = new Date();

                console.log('Демо-режим включен');

            } catch (err) {
                console.error('Ошибка включения демо-режима:', err);
                error.value = 'Ошибка загрузки демо-данных: ' + err.message;
            } finally {
                loading.value = false;
            }
        };

        // Основная загрузка данных
        const loadData = async () => {
            await loadRealData();
        };

        // Фильтрация аудиторий
        const filteredRooms = computed(() => {
            return classrooms.value.filter(room => {
                const buildingMatch = selectedBuilding.value === "all" || room.building?.id === selectedBuilding.value;
                const qualityMatch = selectedQuality.value === "all" || room.airQuality === selectedQuality.value;
                return buildingMatch && qualityMatch;
            });
        });

        // Статистика по качеству воздуха
        const stats = computed(() => {
            const rooms = classrooms.value;
            return {
                total: rooms.length,
                excellent: rooms.filter(r => r.airQuality === "excellent").length,
                good: rooms.filter(r => r.airQuality === "good").length,
                fair: rooms.filter(r => r.airQuality === "fair").length,
                poor: rooms.filter(r => r.airQuality === "poor").length,
                noData: rooms.filter(r => !r.airQuality).length
            };
        });

        // Вспомогательные функции
        const getQualityText = (quality) => {
            const texts = { 
                excellent: "Отличное", 
                good: "Хорошее", 
                fair: "Удовлетворительное", 
                poor: "Плохое" 
            };
            return texts[quality] || "Нет данных";
        };

        const formatTime = (date) => {
            if (!date) return '--:--';
            return new Date(date).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
        };

        // Обновление данных
        const refreshData = async () => {
            if (useDemoMode.value) {
                classrooms.value = generateDemoData(imdfData.value.classrooms);
                lastUpdate.value = new Date();
            } else {
                await loadRealData();
            }
        };

        onMounted(() => {
            loadData();
            
            setInterval(() => {
                currentTime.value = new Date().toLocaleTimeString('ru-RU');
            }, 1000);

            setInterval(() => {
                if (!loading.value) refreshData();
            }, 30000);
        });

        return {
            currentTime,
            classrooms: filteredRooms,
            buildings,
            selectedBuilding,
            selectedQuality,
            stats,
            loading,
            error,
            useDemoMode,
            lastUpdate,
            getQualityText,
            formatTime,
            refreshData,
            enableDemoMode,
            loadRealData
        };
    }
}).mount('#app');