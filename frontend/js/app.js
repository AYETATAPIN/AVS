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
        // Дополнительный маппинг для случаев, если названия немного различаются
        const buildingNameMapping = {
            "учебный корпус 1": "учебный корпус №1",
            "учебный корпус №1": "учебный корпус №1", 
            "ректорат": "ректорат",
            "главный корпус": "главный корпус",
            // можно добавить другие варианты
        };

        // Функция нормализации названий
        const normalizeName = (name) => {
            if (!name) return '';
            let normalized = name.toLowerCase()
                .replace(/[\[\]()]/g, '')
                .replace(/\s+/g, ' ')
                .trim();
            
            // Применяем маппинг если есть
            return buildingNameMapping[normalized] || normalized;
        };

        const sensorMap = {};
        
        // ... остальной код mergeSensorData
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
            
            // Если не нашли данные
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
            }

            const sensorData = await apiService.getAllSensorsData();
            
            // ОТЛАДОЧНАЯ ИНФОРМАЦИЯ
            console.log('Данные получены от API:', {
                timestamp: sensorData.timestamp,
                last_update: sensorData.last_update,
                количество_датчиков: sensorData.data?.length || 0,
                датчики: sensorData.data?.map(s => ({
                    building_name: s.building_name,
                    room_number: s.room_number,
                    co2: s.co2
                }))
            });
            
            classrooms.value = mergeSensorData(imdfData.value.classrooms, sensorData);
            buildings.value = imdfData.value.buildings;
            useDemoMode.value = false;
            lastUpdate.value = sensorData.last_update ? new Date(sensorData.last_update) : new Date(sensorData.timestamp);

            // СТАТИСТИКА СОПОСТАВЛЕНИЯ
            const totalClassrooms = classrooms.value.length;
            const withData = classrooms.value.filter(room => room.hasRealData).length;
            const withoutData = totalClassrooms - withData;
            
            console.log(`Сопоставление данных: ${withData}/${totalClassrooms} аудиторий получили данные`);
            
            if (withoutData > 0) {
                console.log('Аудитории без данных:', classrooms.value
                    .filter(room => !room.hasRealData)
                    .map(room => `${room.buildingName} - ${room.name}`)
                );
            }

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
                // В реальном режиме показываем только аудитории с данными
                // В демо-режиме показываем все (там у всех есть данные)
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
            // В реальном режиме считаем только аудитории с данными
            // В демо-режиме считаем все
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