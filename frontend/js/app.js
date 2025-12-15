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
        
        // Раздельные фильтры для списка и карты
        const selectedBuildingList = ref("all");
        const selectedQualityList = ref("all");
        const selectedFloorList = ref("all");
        const searchQueryList = ref('');
        const selectedQualityMap = ref("all");
        
        const searchTimeout = ref(null);
        
        const apiService = new SensorAPIService();
        const currentView = ref('list');
        const selectedRoom = ref(null);
        const roomHistory = ref([]);
        const historyLoading = ref(false);
        
        // Свойства для аутентификации
        const isAdminAuthenticated = ref(false);
        const showLoginModal = ref(false);
        const loginForm = ref({
            username: '',
            password: ''
        });
        const loginError = ref('');
        const loginLoading = ref(false);
        const authMessage = ref('');
        
        // Проверяем аутентификацию при загрузке
        const checkAuth = async () => {
            const status = await apiService.checkAuthStatus();
            isAdminAuthenticated.value = status.authenticated;
            if (status.authenticated) {
                authMessage.value = 'Вы вошли как администратор';
            }
        };

        // Вход администратора
        const loginAdmin = async () => {
            try {
                loginLoading.value = true;
                loginError.value = '';
                
                if (!loginForm.value.username || !loginForm.value.password) {
                    loginError.value = 'Заполните все поля';
                    return;
                }

                const result = await apiService.loginAdmin(
                    loginForm.value.username, 
                    loginForm.value.password,
                    useDemoMode.value
                );

                if (result.success) {
                    isAdminAuthenticated.value = true;
                    authMessage.value = result.message;
                    showLoginModal.value = false;
                    loginForm.value = { username: '', password: '' };
                    
                    setTimeout(() => {
                        authMessage.value = 'Вы вошли как администратор';
                    }, 3000);
                } else {
                    loginError.value = result.message;
                }
            } catch (err) {
                console.error('Ошибка входа:', err);
                loginError.value = 'Произошла ошибка при входе';
            } finally {
                loginLoading.value = false;
            }
        };

        // Выход администратора
        const logoutAdmin = () => {
            const result = apiService.logoutAdmin();
            isAdminAuthenticated.value = false;
            authMessage.value = result.message;
            
            setTimeout(() => {
                authMessage.value = '';
            }, 3000);
        };

        // Открытие модального окна входа
        const openLoginModal = () => {
            loginForm.value = { username: '', password: '' };
            loginError.value = '';
            showLoginModal.value = true;
        };

        // Закрытие модального окна
        const closeLoginModal = () => {
            showLoginModal.value = false;
            loginForm.value = { username: '', password: '' };
            loginError.value = '';
        };
        
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
                
                roomHistory.value = await apiService.getSensorHistory(sensorId, 24);
                
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
                    
                    // Используем filteredRoomsForMap для карты
                    campusMap = new CampusMap('campus-map', imdfData.value, filteredRoomsForMap.value);
                    campusMap.init();
                    
                    // Добавляем обработчик смены этажа
                    campusMap.onFloorChange = (floor) => {
                        console.log(`Этаж изменен на карте: ${floor}`);
                    };
                    
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
        };

        // Обновление данных на карте
        const updateMapData = () => {
            if (campusMap) {
                campusMap.updateClassrooms(filteredRoomsForMap.value);
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
                    hasRealData: true,
                    sensorId: `demo-${room.id}`
                };
            });
        };

        // Объединяем данные IMDF с данными датчиков
        const mergeSensorData = (classrooms, sensorDataArray) => {
            console.log('Данные с сервера (первые 10):', sensorDataArray?.slice(0, 10));
            console.log('Аудитории IMDF (первые 10):', classrooms.slice(0, 10));

            const buildingNameMapping = {
                "учебный корпус 1": "учебный корпус №1",
                "учебный корпус №1": "учебный корпус №1", 
                "ректорат": "ректорат",
                "главный корпус": "главный корпус",
                "аудиторный корпус": "аудиторный корпус"
            };

            const normalizeName = (name) => {
                if (!name) return '';
                let normalized = name.toLowerCase()
                    .replace(/[\[\]()]/g, '')
                    .replace(/\s+/g, ' ')
                    .trim();
                
                return buildingNameMapping[normalized] || normalized;
            };

            const normalizeRoomNumber = (roomNumber) => {
                return roomNumber ? roomNumber.toString().toLowerCase().replace(/\s/g, '') : '';
            };

            const sensorMap = {};
            
            sensorDataArray?.forEach(sensor => {
                if (sensor.buildingName && sensor.roomNumber) {
                    const normalizedBuilding = normalizeName(sensor.buildingName);
                    const normalizedRoom = normalizeRoomNumber(sensor.roomNumber);
                    const key = `${normalizedBuilding}|${normalizedRoom}`;
                    sensorMap[key] = sensor;
                }
            });

            return classrooms.map(room => {
                if (room.buildingName && room.roomNumber) {
                    const normalizedBuilding = normalizeName(room.buildingName);
                    const normalizedRoom = normalizeRoomNumber(room.roomNumber);
                    const key = `${normalizedBuilding}|${normalizedRoom}`;
                    const sensor = sensorMap[key];
                    
                    if (sensor) {
                        return {
                            ...room,
                            co2: sensor.co2,
                            temperature: sensor.temperature,
                            humidity: sensor.humidity,
                            airQuality: calculateAirQuality(sensor.co2),
                            lastUpdate: new Date(sensor.ts),
                            hasRealData: true,
                            sensorId: sensor.sensorId
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

                const sensorDataArray = await apiService.getAllSensorsData();
                classrooms.value = mergeSensorData(imdfData.value.classrooms, sensorDataArray);
                updateMapData();
                buildings.value = imdfData.value.buildings;
                useDemoMode.value = false;
                lastUpdate.value = sensorDataArray?.length > 0 ? new Date(sensorDataArray[0].ts) : new Date();

            } catch (err) {
                console.error('Ошибка загрузки реальных данных:', err);
                error.value = 'Не удалось подключиться к серверу датчиков';
                // Автоматически переключаемся в демо-режим при ошибке
                await enableDemoMode();
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

        // Функция для извлечения чисел из строки
        const extractNumbers = (str) => {
            if (!str) return '';
            const match = str.toString().match(/\d+/);
            return match ? match[0] : '';
        };

        // Обработка поиска
        const handleSearch = () => {
            if (searchTimeout.value) {
                clearTimeout(searchTimeout.value);
            }
            
            searchTimeout.value = setTimeout(() => {
                // Триггерим обновление
                console.log('Поиск обновлен:', searchQueryList.value);
            }, 300);
        };

        // Фильтрация аудиторий для списка
        const filteredRooms = computed(() => {
            if (!classrooms.value) return [];
            
            let filtered = classrooms.value.filter(room => {
                if (!useDemoMode.value && !room.hasRealData) {
                    return false;
                }

                const buildingMatch = selectedBuildingList.value === "all" || room.building?.id === selectedBuildingList.value;
                const qualityMatch = selectedQualityList.value === "all" || room.airQuality === selectedQualityList.value;
                const floorMatch = selectedFloorList.value === "all" || room.floor === selectedFloorList.value;
                
                // Логика поиска
                let searchMatch = true;
                if (searchQueryList.value) {
                    const searchNumber = extractNumbers(searchQueryList.value);
                    const roomNumber = extractNumbers(room.name) || extractNumbers(room.roomNumber);
                    
                    if (searchNumber && roomNumber) {
                        searchMatch = roomNumber.startsWith(searchNumber);
                    } else if (searchQueryList.value.trim()) {
                        const searchLower = searchQueryList.value.toLowerCase();
                        const roomNameLower = room.name ? room.name.toLowerCase() : '';
                        const roomNumberLower = room.roomNumber ? room.roomNumber.toString().toLowerCase() : '';
                        searchMatch = roomNameLower.includes(searchLower) || 
                                      roomNumberLower.includes(searchLower);
                    }
                }
                
                return buildingMatch && qualityMatch && floorMatch && searchMatch;
            });
            
            return filtered;
        });

        // Фильтрация для карты (только по качеству)
        const filteredRoomsForMap = computed(() => {
            if (!classrooms.value) return [];
            
            return classrooms.value.filter(room => {
                if (!useDemoMode.value && !room.hasRealData) {
                    return false;
                }
                
                // Только фильтр по качеству для карты
                const qualityMatch = selectedQualityMap.value === "all" || room.airQuality === selectedQualityMap.value;
                return qualityMatch;
            });
        });

        watch(selectedQualityMap, () => {
            if (campusMap && currentView.value === 'map') {
                updateMapData();
            }
        });

        watch(selectedRoom, (newRoom) => {
            if (newRoom && currentView.value === 'details') {
                loadRoomHistory();
            }
        });

        // Основная загрузка данных - сначала пытаемся загрузить реальные, если не получается - демо
        const loadData = async () => {
            try {
                await loadRealData();
            } catch (err) {
                console.log('Не удалось загрузить реальные данные, переключаемся в демо-режим');
                await enableDemoMode();
            }
        };

        // Статистика по качеству воздуха
        const stats = computed(() => {
            const roomsToCount = useDemoMode.value 
                ? classrooms.value 
                : classrooms.value.filter(room => room.hasRealData);
            
            // Фильтруем еще раз по текущим фильтрам списка
            let filtered = roomsToCount.filter(room => {
                const buildingMatch = selectedBuildingList.value === "all" || room.building?.id === selectedBuildingList.value;
                const qualityMatch = selectedQualityList.value === "all" || room.airQuality === selectedQualityList.value;
                const floorMatch = selectedFloorList.value === "all" || room.floor === selectedFloorList.value;
                return buildingMatch && qualityMatch && floorMatch;
            });
            
            return {
                total: filtered.length,
                excellent: filtered.filter(r => r.airQuality === "excellent").length,
                good: filtered.filter(r => r.airQuality === "good").length,
                fair: filtered.filter(r => r.airQuality === "fair").length,
                poor: filtered.filter(r => r.airQuality === "poor").length,
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
                updateMapData();
            } else {
                await loadRealData();
            }
        };
        
        onMounted(() => {
            checkAuth();
            loadData();
            
            setInterval(() => {
                currentTime.value = new Date().toLocaleTimeString('ru-RU');
            }, 1000);

            // Автообновление только для демо-режима
            setInterval(() => {
                if (!loading.value && useDemoMode.value) {
                    refreshData();
                }
            }, 30000);
        });

        return {
            currentTime,
            classrooms,
            buildings,
            selectedBuildingList,
            selectedQualityList,
            selectedFloorList,
            searchQueryList,
            selectedQualityMap,
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
            historyLoading,
            isAdminAuthenticated,
            showLoginModal,
            loginForm,
            loginError,
            loginLoading,
            authMessage,
            loginAdmin,
            logoutAdmin,
            openLoginModal,
            closeLoginModal,
            handleSearch,
            filteredRooms
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