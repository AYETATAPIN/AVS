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
        
        // Добавляем свойства для аутентификации
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

                // Явно передаем useDemoMode.value
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
                    
                    // Показываем сообщение об успехе на 3 секунды
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
            
            // Скрываем сообщение через 3 секунды
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
        const mergeSensorData = (classrooms, sensorDataArray) => {
            console.log('Данные с сервера (первые 10):', sensorDataArray.slice(0, 10));
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
            
            sensorDataArray.forEach(sensor => {
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
                lastUpdate.value = sensorDataArray.length > 0 ? new Date(sensorDataArray[0].ts) : new Date();

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
            checkAuth();
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
            closeLoginModal
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