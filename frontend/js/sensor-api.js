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