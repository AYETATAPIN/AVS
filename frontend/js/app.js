// Vue приложение
const { createApp, ref, computed, onMounted, watch } = Vue; 
let campusMap = null;

// Создаем приложение и сохраняем его в переменную
const app = createApp({
    setup() {
        const currentTime = ref(new Date().toLocaleTimeString('ru-RU'));
        const classrooms = ref([]);
        const buildings = ref([]);
        const loading = ref(true);
        const error = ref(null);
        const useDemoMode = ref(false);
        const lastUpdate = ref(null);
        const imdfData = ref(null);
        const selectedFloor = ref("all");
        const availableFloors = ref([]);
        const selectedBuilding = ref("all");
        const selectedQuality = ref("all");
        
        const apiService = new SensorAPIService();
        const currentView = ref('list');
        const selectedRoom = ref(null);
        const roomHistory = ref([]);
        const historyLoading = ref(false);

        // Функция для показа деталей комнаты
        const showRoomDetails = (roomId) => {
            selectedRoom.value = classrooms.value.find(room => room.id === roomId);
            currentView.value = 'details';
            loadRoomHistory();
        };

        const loadRoomHistory = async () => {
            if (!selectedRoom.value) return;
            
            try {
                historyLoading.value = true;
                const sensorId = selectedRoom.value.sensorId || selectedRoom.value.id;
                console.log('Загрузка исторических данных для:', {
                    room: selectedRoom.value.name,
                    sensorId: sensorId,
                    hasRealData: selectedRoom.value.hasRealData,
                    useDemoMode: useDemoMode.value
                });
                
                roomHistory.value = await apiService.getSensorHistory(sensorId, 24);
                console.log('Исторические данные загружены:', roomHistory.value.length, 'записей');
                console.log('Пример данных:', roomHistory.value.slice(0, 3));
                
            } catch (err) {
                console.error('Ошибка загрузки исторических данных:', err);
                roomHistory.value = [];
            } finally {
                historyLoading.value = false;
            }
        };

        // Функция инициализации карты
        const initMap = () => {
            if (!imdfData.value) {
                console.warn('IMDF данные не загружены');
                return;
            }
            
            try {
                console.log('Инициализация карты...');
                
                setTimeout(() => {
                    if (typeof CampusMap === 'undefined') {
                        console.error('CampusMap не определен');
                        error.value = 'Ошибка загрузки карты: CampusMap не найден';
                        return;
                    }
                    
                    const mapContainer = document.getElementById('campus-map');
                    if (!mapContainer) {
                        console.error('Контейнер карты не найден');
                        return;
                    }
                    
                    if (mapContainer._leaflet_id) {
                        mapContainer._leaflet_id = null;
                        mapContainer.innerHTML = '';
                    }
                    
                    campusMap = new CampusMap('campus-map', imdfData.value, classrooms.value);
                    campusMap.init();
                    
                    window.showRoomDetails = showRoomDetails;
                    
                    console.log('Карта успешно инициализирована');
                }, 100);
            } catch (err) {
                console.error('Ошибка инициализации карты:', err);
                error.value = 'Ошибка загрузки карты: ' + err.message;
            }
        };

        // Обновление доступных этажей
        const updateAvailableFloors = () => {
            if (!imdfData.value) return;
            
            const floors = new Set();
            imdfData.value.classrooms.forEach(classroom => {
                if (classroom.floor) {
                    floors.add(classroom.floor);
                }
            });
            
            availableFloors.value = Array.from(floors).sort((a, b) => {
                const order = { 'Цокольный': -1, '1': 0, '2': 1, '3': 2, '4': 3, '5': 4 };
                return (order[a] || parseInt(a)) - (order[b] || parseInt(b));
            });
            
            console.log('Доступные этажи:', availableFloors.value);
        };

        // Обновление данных на карте
        const updateMapData = () => {
            if (campusMap) {
                campusMap.updateClassrooms(classrooms.value);
            }
        };

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
                    hasRealData: true, // В демо-режиме показываем, что данные есть
                    sensorId: `demo-${room.id}`
                };
            });
        };

        // Объединяем данные IMDF с данными датчиков
        const mergeSensorData = (classrooms, sensorData) => {
            const buildingNameMapping = {
                "учебный корпус 1": "учебный корпус №1",
                "учебный корпус №1": "учебный корпус №1", 
                "ректорат": "ректорат",
                "главный корпус": "главный корпус",
            };

            const normalizeName = (name) => {
                if (!name) return '';
                let normalized = name.toLowerCase()
                    .replace(/[\[\]()]/g, '')
                    .replace(/\s+/g, ' ')
                    .trim();
                
                return buildingNameMapping[normalized] || normalized;
            };

            const sensorMap = {};
            
            sensorData.data?.forEach(sensor => {
                if (sensor.building_name && sensor.room_number) {
                    const normalizedBuilding = normalizeName(sensor.building_name);
                    const key = `${normalizedBuilding}|${sensor.room_number}`;
                    sensorMap[key] = sensor;
                }
            });

            const lastUpdateTime = sensorData.last_update ? new Date(sensorData.last_update) : new Date(sensorData.timestamp);

            return classrooms.map(room => {
                if (room.buildingName && room.roomNumber) {
                    const normalizedBuilding = normalizeName(room.buildingName);
                    const key = `${normalizedBuilding}|${room.roomNumber}`;
                    const sensor = sensorMap[key];
                    
                    if (sensor) {
                        return {
                            ...room,
                            co2: sensor.co2,
                            temperature: sensor.temperature,
                            humidity: sensor.humidity,
                            airQuality: calculateAirQuality(sensor.co2),
                            lastUpdate: lastUpdateTime,
                            hasRealData: true,
                            sensorId: sensor.sensor_id
                        };
                    }
                }
                
                return {
                    ...room,
                    co2: null,
                    temperature: null,
                    humidity: null,
                    airQuality: null,
                    lastUpdate: null,
                    hasRealData: false,
                    sensorId: null
                };
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
                    updateAvailableFloors();
                }

                const sensorData = await apiService.getAllSensorsData();
                classrooms.value = mergeSensorData(imdfData.value.classrooms, sensorData);
                updateMapData();
                buildings.value = imdfData.value.buildings;
                useDemoMode.value = false;
                lastUpdate.value = sensorData.last_update ? new Date(sensorData.last_update) : new Date(sensorData.timestamp);

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
                    updateAvailableFloors(); 
                }

                classrooms.value = generateDemoData(imdfData.value.classrooms);
                updateMapData();
                buildings.value = imdfData.value.buildings;
                useDemoMode.value = true;
                lastUpdate.value = new Date();

            } catch (err) {
                console.error('Ошибка включения демо-режима:', err);
                error.value = 'Ошибка загрузки демо-данных: ' + err.message;
            } finally {
                loading.value = false;
            }
        };

        watch(selectedFloor, (newFloor) => {
            if (campusMap) {
                campusMap.setFloor(newFloor);
            }
        });

        watch(selectedRoom, (newRoom) => {
            if (newRoom && currentView.value === 'details') {
                loadRoomHistory();
            }
        });

        // Основная загрузка данных
        const loadData = async () => {
            await loadRealData();
        };

        // Фильтрация аудиторий
        const filteredRooms = computed(() => {
            return classrooms.value.filter(room => {
                if (!useDemoMode.value && !room.hasRealData) {
                    return false;
                }

                const buildingMatch = selectedBuilding.value === "all" || room.building?.id === selectedBuilding.value;
                const qualityMatch = selectedQuality.value === "all" || room.airQuality === selectedQuality.value;
                return buildingMatch && qualityMatch;
            });
        });

        // Статистика по качеству воздуха
        const stats = computed(() => {
            const roomsToCount = useDemoMode.value 
                ? classrooms.value 
                : classrooms.value.filter(room => room.hasRealData);
            
            return {
                total: roomsToCount.length,
                excellent: roomsToCount.filter(r => r.airQuality === "excellent").length,
                good: roomsToCount.filter(r => r.airQuality === "good").length,
                fair: roomsToCount.filter(r => r.airQuality === "fair").length,
                poor: roomsToCount.filter(r => r.airQuality === "poor").length,
                noData: useDemoMode.value ? 0 : classrooms.value.filter(r => !r.hasRealData).length
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
            selectedFloor,
            availableFloors,
            stats,
            loading,
            error,
            useDemoMode,
            lastUpdate,
            getQualityText,
            formatTime,
            refreshData,
            enableDemoMode,
            loadRealData,
            currentView,
            selectedRoom,
            showRoomDetails,
            initMap,
            roomHistory,
            historyLoading
        };
    }
});

// Теперь регистрируем компоненты
console.log('Регистрация компонентов...');
if (typeof ChartComponents !== 'undefined') {
    console.log('ChartComponents найден:', Object.keys(ChartComponents));
    Object.entries(ChartComponents).forEach(([name, component]) => {
        app.component(name, component);
        console.log('Зарегистрирован компонент:', name);
    });
} else {
    console.error('ChartComponents не определен');
    console.log('Доступные глобальные переменные:', Object.keys(window));
}

// Монтируем приложение
app.mount('#app');