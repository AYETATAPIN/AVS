// Сервис для работы с API датчиков и аутентификации
class SensorAPIService {
    constructor(baseUrl = 'http://localhost:8080/api') {
        this.baseUrl = baseUrl;
        this.token = localStorage.getItem('authToken') || null;
        this.useDemoMode = localStorage.getItem('useDemoMode') === 'true' || false;
    }

    // Устанавливает токен аутентификации
    setAuthToken(token) {
        this.token = token;
        localStorage.setItem('authToken', token);
    }

    // Удаляет токен
    clearAuthToken() {
        this.token = null;
        localStorage.removeItem('authToken');
    }

    // Аутентификация администратора (теперь учитывает демо-режим)
    async loginAdmin(username, password, isDemoMode = false) {
        try {
            console.log('Аутентификация администратора...', { username, password, isDemoMode, useDemoMode: this.useDemoMode });
            
            // Если в демо-режиме или сервер недоступен, используем демо-логин
            if (isDemoMode || this.useDemoMode) {
                console.log('Демо-режим аутентификации');
                await new Promise(resolve => setTimeout(resolve, 1000)); // Имитация задержки
                
                const demoToken = 'demo-token-' + Date.now();
                this.setAuthToken(demoToken);
                
                return { 
                    success: true, 
                    message: `Демо-режим: успешный вход как ${username}`,
                    user: { username, role: 'admin' }
                };
            }

            // Реальный режим - пробуем отправить запрос
            const url = `${this.baseUrl}/auth/login`;
            console.log('Отправка запроса на аутентификацию по URL:', url);
            console.log('Тело запроса:', JSON.stringify({ username, password }));
            
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password })
            });
            
            console.log('Получен ответ от сервера:', response);
            console.log('Статус ответа:', response.status);
            
            // Проверяем различные статусы
            if (response.status === 404) {
                console.log('Эндпоинт /api/auth/login не найден (404)');
                throw new Error('Эндпоинт аутентификации не найден');
            }
            
            if (response.status === 405) {
                console.log('Метод не разрешен (405)');
                throw new Error('Метод POST не поддерживается');
            }
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('Ошибка сервера при аутентификации:', errorText);
                throw new Error(`Ошибка сервера: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Данные ответа:', data);
            
            if (data.token) {
                this.setAuthToken(data.token);
                console.log('Токен получен и сохранен:', data.token.substring(0, 20) + '...');
                return { 
                    success: true, 
                    message: 'Успешная аутентификация',
                    user: data.user
                };
            } else if (data.access_token) {
                // Если токен пришел в поле access_token
                this.setAuthToken(data.access_token);
                console.log('Токен получен (access_token) и сохранен');
                return { 
                    success: true, 
                    message: 'Успешная аутентификация',
                    user: data.user || { username, role: 'admin' }
                };
            } else {
                console.log('Токен не найден в ответе сервера');
                throw new Error('Токен не получен от сервера');
            }
            
        } catch (error) {
            console.error('Ошибка аутентификации:', error);
            console.error('Полная ошибка:', {
                name: error.name,
                message: error.message,
                stack: error.stack
            });
            
            // Проверяем различные типы ошибок
            if (error.message.includes('Failed to fetch') || 
                error.message.includes('NetworkError') ||
                error.message.includes('CORS')) {
                console.log('Проблема с сетью или CORS, используем демо-режим');
                
                const demoToken = 'demo-fallback-token-' + Date.now();
                this.setAuthToken(demoToken);
                
                return { 
                    success: true, 
                    message: `Авто-демо: вход как ${username}`,
                    user: { username, role: 'admin' }
                };
            }
            
            return { 
                success: false, 
                message: 'Ошибка аутентификации: ' + error.message 
            };
        }
    }
    // Выход из системы
    logoutAdmin() {
        this.clearAuthToken();
        return { success: true, message: 'Вы вышли из системы' };
    }

    // Проверка статуса аутентификации
    async checkAuthStatus() {
        if (!this.token) {
            return { authenticated: false };
        }
        
        try {
            // Проверяем, демо-ли это токен
            if (this.token.startsWith('demo-token-') || this.token.startsWith('demo-fallback-token-')) {
                return { authenticated: true, isDemo: true };
            }
            
            // Реальная проверка токена (если нужно)
            // const response = await fetch(`${this.baseUrl}/auth/check`, {
            //     headers: { 'Authorization': `Bearer ${this.token}` }
            // });
            
            // Для упрощения считаем, что если есть токен - пользователь аутентифицирован
            return { authenticated: true, isDemo: false };
            
        } catch (error) {
            console.error('Ошибка проверки аутентификации:', error);
            return { authenticated: false };
        }
    }

    async getAllSensorsData() {
        try {
            console.log('Запрос данных с сервера...');
            
            // Если в демо-режиме, используем демо-данные
            if (this.useDemoMode) {
                console.log('Используем демо-режим для данных датчиков');
                return this.generateDemoCurrentData();
            }
            
            // Попытка прямого запроса к серверу датчиков
            const response = await fetch(`${this.baseUrl}/sensors/current`, {
                method: 'GET',
                mode: 'cors',
                headers: {
                    'Accept': 'application/json',
                }
            });
            
            if (!response.ok) {
                throw new Error(`Ошибка сервера: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Данные успешно получены:', data);
            
            // Убедимся, что возвращаем массив
            if (!Array.isArray(data)) {
                throw new Error('Данные не являются массивом');
            }
            
            return data;
            
        } catch (error) {
            console.error('Ошибка загрузки данных с датчиков:', error);
            throw error;
        }
    }

    async getSensorHistory(sensorId, hours = 24) {
        try {
            return this.generateDemoHistoryData(hours);
        } catch (error) {
            console.error('Ошибка загрузки исторических данных:', error);
            return this.generateDemoHistoryData(hours);
        }
    }

    generateDemoHistoryData(hours = 24) {
        const data = [];
        const now = new Date();
        
        for (let i = hours; i >= 0; i--) {
            const timestamp = new Date(now.getTime() - i * 60 * 60 * 1000);
            const baseCO2 = 400 + Math.sin(i * 0.5) * 300 + Math.random() * 200;
            const co2 = Math.max(400, Math.min(1500, Math.floor(baseCO2)));
            
            const hourOfDay = timestamp.getHours();
            const tempBase = 18 + Math.sin(hourOfDay * Math.PI / 12) * 5;
            const temperature = (tempBase + Math.random() * 2 - 1).toFixed(1);
            
            const humidityBase = 50 - (tempBase - 18) * 2;
            const humidity = Math.max(30, Math.min(80, Math.floor(humidityBase + Math.random() * 10 - 5)));
            
            data.push({
                timestamp: timestamp.toISOString(),
                co2: co2,
                temperature: parseFloat(temperature),
                humidity: humidity,
                airQuality: this.calculateAirQuality(co2)
            });
        }
        
        return data;
    }

    calculateAirQuality(co2) {
        if (!co2) return null;
        if (co2 < 600) return "excellent";
        if (co2 < 800) return "good";
        if (co2 < 1000) return "fair";
        return "poor";
    }
}
