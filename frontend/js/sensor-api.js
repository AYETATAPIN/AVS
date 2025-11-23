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

    // метод для получения исторических данных
    async getSensorHistory(sensorId, hours = 24) {
        try {
            console.log(`Запрос исторических данных для датчика: ${sensorId}, часов: ${hours}`);
            
            // В реальном приложении здесь был бы запрос к API
            // Для демо сгенерируем данные
            const demoData = this.generateDemoHistoryData(hours);
            console.log('Сгенерировано демо-данных:', demoData.length);
            return demoData;
        } catch (error) {
            console.error('Ошибка загрузки исторических данных:', error);
            // В случае ошибки вернем демо-данные
            return this.generateDemoHistoryData(hours);
        }
    }

    // Генератор демо-исторических данных
    generateDemoHistoryData(hours = 24) {
        const data = [];
        const now = new Date();
        
        // Генерируем данные с интервалом в 1 час
        for (let i = hours; i >= 0; i--) {
            const timestamp = new Date(now.getTime() - i * 60 * 60 * 1000);
            const baseCO2 = 400 + Math.sin(i * 0.5) * 300 + Math.random() * 200;
            const co2 = Math.max(400, Math.min(1500, Math.floor(baseCO2)));
            
            // Температура 
            const hourOfDay = timestamp.getHours();
            const tempBase = 18 + Math.sin(hourOfDay * Math.PI / 12) * 5;
            const temperature = (tempBase + Math.random() * 2 - 1).toFixed(1);
            
            // Влажность 
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
        
        console.log('Сгенерированы демо-данные:', data.length, 'записей');
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