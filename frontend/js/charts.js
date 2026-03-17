// charts.js

const ChartComponents = {
    LineChart: {
        name: 'LineChart',
        template: `
            <div class="chart-container">
                <canvas ref="chartCanvas" v-show="hasData"></canvas>
                <div v-show="!hasData" class="no-chart-data">
                    <p>Нет данных для отображения графика</p>
                </div>
            </div>
        `,
        props: {
            data: { type: Array, required: true },
            title: { type: String, default: 'Исторические данные' }
        },
        data() {
            return {
                chart: null,
                isMounted: false
            };
        },
        computed: {
            hasData() {
                return this.data && this.data.length > 0;
            }
        },
        mounted() {
            this.isMounted = true;
            if (this.hasData) {
                this.$nextTick(this.renderChart);
            }
        },
        beforeUnmount() {
            if (this.chart) {
                this.chart.destroy();
                this.chart = null;
            }
        },
        watch: {
            data: {
                handler() {
                    if (this.isMounted) {
                        this.$nextTick(this.renderChart);
                    }
                },
                deep: true
            }
        },
        methods: {
            renderChart() {
                if (this.chart) {
                    this.chart.destroy();
                    this.chart = null;
                }

                if (!this.hasData) return;

                const canvas = this.$refs.chartCanvas;
                if (!canvas) {
                    console.warn('Canvas ref not found');
                    return;
                }

                const ctx = canvas.getContext('2d');
                if (!ctx) {
                    console.error('Не удалось получить контекст canvas');
                    return;
                }

                // Подготовка данных
                const labels = this.data.map(item => {
                    const date = new Date(item.ts);
                    return date.toLocaleTimeString('ru-RU', {
                        hour: '2-digit',
                        minute: '2-digit'
                    });
                });

                const co2Data = this.data.map(item => item.co2);
                const temperatureData = this.data.map(item => item.temperature);
                const humidityData = this.data.map(item => item.humidity);

                try {
                    this.chart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: [
                                {
                                    label: 'CO₂ (ppm)',
                                    data: co2Data,
                                    borderColor: '#3b82f6',
                                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                    borderWidth: 2,
                                    tension: 0.4,
                                    yAxisID: 'y'
                                },
                                {
                                    label: 'Температура (°C)',
                                    data: temperatureData,
                                    borderColor: '#ef4444',
                                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                                    borderWidth: 2,
                                    tension: 0.4,
                                    yAxisID: 'y1'
                                },
                                {
                                    label: 'Влажность (%)',
                                    data: humidityData,
                                    borderColor: '#10b981',
                                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                                    borderWidth: 2,
                                    tension: 0.4,
                                    yAxisID: 'y2'
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            interaction: { mode: 'index', intersect: false },
                            scales: {
                                x: { title: { display: true, text: 'Время' } },
                                y: {
                                    type: 'linear',
                                    display: true,
                                    position: 'left',
                                    title: { display: true, text: 'CO₂ (ppm)' },
                                    grid: { drawOnChartArea: false }
                                },
                                y1: {
                                    type: 'linear',
                                    display: true,
                                    position: 'right',
                                    title: { display: true, text: 'Температура (°C)' },
                                    grid: { drawOnChartArea: false }
                                },
                                y2: {
                                    type: 'linear',
                                    display: true,
                                    position: 'right',
                                    title: { display: true, text: 'Влажность (%)' },
                                    offset: true,
                                    grid: { drawOnChartArea: false }
                                }
                            },
                            plugins: {
                                title: { display: true, text: this.title },
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            let label = context.dataset.label || '';
                                            if (label) label += ': ';
                                            if (context.parsed.y !== null) {
                                                label += context.parsed.y;
                                                if (context.dataset.label.includes('CO₂')) label += ' ppm';
                                                else if (context.dataset.label.includes('Температура')) label += '°C';
                                                else if (context.dataset.label.includes('Влажность')) label += '%';
                                            }
                                            return label;
                                        }
                                    }
                                }
                            }
                        }
                    });
                    console.log('График успешно создан');
                } catch (error) {
                    console.error('Ошибка создания графика:', error);
                }
            }
        }
    },

    QualityChart: {
        name: 'QualityChart',
        template: `
            <div class="chart-container">
                <canvas ref="chartCanvas" v-show="hasData"></canvas>
                <div v-show="!hasData" class="no-chart-data">
                    <p>Нет данных для отображения графика</p>
                </div>
            </div>
        `,
        props: {
            data: { type: Array, required: true }
        },
        data() {
            return {
                chart: null,
                isMounted: false,
                qualityColors: {
                    excellent: '#10b981',
                    good: '#3b82f6',
                    fair: '#f59e0b',
                    poor: '#ef4444'
                }
            };
        },
        computed: {
            hasData() {
                return this.data && this.data.length > 0;
            }
        },
        mounted() {
            this.isMounted = true;
            if (this.hasData) {
                this.$nextTick(this.renderChart);
            }
        },
        beforeUnmount() {
            if (this.chart) {
                this.chart.destroy();
                this.chart = null;
            }
        },
        watch: {
            data: {
                handler() {
                    if (this.isMounted) {
                        this.$nextTick(this.renderChart);
                    }
                },
                deep: true
            }
        },
        methods: {
            renderChart() {
                if (this.chart) {
                    this.chart.destroy();
                    this.chart = null;
                }

                if (!this.hasData) return;

                const canvas = this.$refs.chartCanvas;
                if (!canvas) return;
                const ctx = canvas.getContext('2d');
                if (!ctx || canvas.width === 0 || canvas.height === 0) {
                    console.warn('Canvas not ready, retrying...');
                    setTimeout(() => this.renderChart(), 100);
                    return;
                }
                
                // Группируем данные по качеству воздуха
                const qualityCounts = {
                    excellent: 0,
                    good: 0,
                    fair: 0,
                    poor: 0
                };

                this.data.forEach(item => {
                    if (item.airQuality && qualityCounts[item.airQuality] !== undefined) {
                        qualityCounts[item.airQuality]++;
                    }
                });

                const labels = {
                    excellent: 'Отличное',
                    good: 'Хорошее',
                    fair: 'Удовлетворительное',
                    poor: 'Плохое'
                };

                try {
                    this.chart = new Chart(ctx, {
                        type: 'doughnut',
                        data: {
                            labels: Object.keys(qualityCounts).map(key => labels[key]),
                            datasets: [{
                                data: Object.values(qualityCounts),
                                backgroundColor: Object.keys(qualityCounts).map(key => this.qualityColors[key]),
                                borderWidth: 2,
                                borderColor: '#fff'
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { position: 'bottom' },
                                title: { display: true, text: 'Распределение качества воздуха' },
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            const label = context.label || '';
                                            const value = context.parsed;
                                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                            const percentage = Math.round((value / total) * 100);
                                            return `${label}: ${value} (${percentage}%)`;
                                        }
                                    }
                                }
                            }
                        }
                    });
                    console.log('График качества успешно создан');
                } catch (error) {
                    console.error('Ошибка создания графика качества:', error);
                }
            }
        }
    }
};