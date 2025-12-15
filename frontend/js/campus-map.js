// Компонент карты кампуса
class CampusMap {
    constructor(containerId, imdfData, classrooms) {
        this.containerId = containerId;
        this.imdfData = imdfData;
        this.classrooms = classrooms;
        this.allClassrooms = classrooms;
        this.map = null;
        this.roomLayers = new Map();
        this.sensorLayers = new Map();
        this.currentFloor = "all";
    }

    init() {
        try {
            console.log('Инициализация карты...');
            
            this.map = L.map(this.containerId).setView([54.844, 83.09], 17);

            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: false
            }).addTo(this.map);
            this.createCustomAttribution();
            
            // Сначала рендерим базовые элементы
            this.renderVenue();
            this.renderBuildings();
            this.renderOpenings();
            
            // Затем создаем контрол этажей
            this.createFloorControl();
            
            // И рендерим аудитории (будет показан этаж по умолчанию)
            this.renderClassrooms();
            this.updateLegend(this.currentFloor);
            
            console.log('Карта успешно инициализирована');
            return this.map;
        } catch (error) {
            console.error('Ошибка инициализации карты:', error);
            throw error;
        }
    }

    createCustomAttribution() {
        // Создаем свой контрол атрибуции
        const customAttribution = L.control.attribution();
        customAttribution.addTo(this.map);
        
        // Устанавливаем нашу атрибуцию
        customAttribution.setPrefix(`
            <a href="https://leafletjs.com" title="A JavaScript library for interactive maps">Leaflet</a>
            <span style="
                display: inline-block;
                width: 12px;
                height: 8px;
                margin: 0 2px;
                background: linear-gradient(to bottom, 
                    #FFFFFF 0%, #FFFFFF 33%, 
                    #0033A0 33%, #0033A0 66%, 
                    #D52B1E 66%, #D52B1E 100%);
                border: 1px solid rgba(0,0,0,0.2);
                vertical-align: baseline;
            "></span>
            | © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors
        `);
        
        // Агрессивно скрываем любой стандартный флаг
        setInterval(() => {
            const standardFlags = document.querySelectorAll('.leaflet-attribution-flag');
            standardFlags.forEach(flag => {
                flag.style.display = 'none';
                flag.style.visibility = 'hidden';
                flag.style.opacity = '0';
                flag.style.width = '0';
                flag.style.height = '0';
            });
        }, 1000);
    }

    setFloor(floor) {
        this.currentFloor = floor;
        console.log(`Установлен этаж: ${floor}`);
        
        // Обновляем отображение аудиторий
        const filteredClassrooms = this.filterClassroomsByFloor(this.allClassrooms, floor);
        this.clearClassroomLayers();
        
        if (filteredClassrooms && filteredClassrooms.length > 0) {
            filteredClassrooms.forEach(classroom => {
                if (classroom.unit && classroom.unit.geometry) {
                    const color = this.getRoomColor(classroom);
                    
                    const roomLayer = L.geoJSON(classroom.unit.geometry, {
                        style: {
                            color: color,
                            fillColor: color,
                            fillOpacity: 0.7,
                            weight: 2
                        }
                    }).addTo(this.map);

                    this.roomLayers.set(classroom.id, roomLayer);
                    roomLayer.bindPopup(() => this.createRoomPopup(classroom));
                    
                    roomLayer.on('mouseover', function() {
                        this.setStyle({ weight: 4, fillOpacity: 0.9 });
                    });
                    roomLayer.on('mouseout', function() {
                        this.setStyle({ weight: 2, fillOpacity: 0.7 });
                    });
                }
            });
        }
        
        // Обновляем выбранную кнопку
        this.selectFloorButton(floor);
        
        // Обновляем легенду
        this.updateLegend(floor);
        
        // Вызываем коллбэк, если есть
        if (this.onFloorChange) {
            this.onFloorChange(floor);
        }
    }


    filterClassroomsByFloor(classrooms, floor) {
        if (floor === "all") {
            return classrooms;
        }
        return classrooms.filter(classroom => classroom.floor === floor);
    }

    renderVenue() {
        if (!this.imdfData.venues || this.imdfData.venues.length === 0) {
            console.warn('Нет данных о территории университета');
            return;
        }

        this.imdfData.venues.forEach(venue => {
            if (venue.geometry) {
                L.geoJSON(venue.geometry, {
                    style: {
                        color: '#3b82f6',
                        fillColor: '#dbeafe',
                        fillOpacity: 0.3,
                        weight: 3
                    }
                }).addTo(this.map).bindPopup(`
                    <div class="map-popup">
                        <h3>${venue.properties?.name?.ru || 'НГУ'}</h3>
                        <p>${venue.properties?.address_id ? this.getAddressText(venue.properties.address_id) : ''}</p>
                        ${venue.properties?.website ? `<p><a href="${venue.properties.website}" target="_blank">${venue.properties.website}</a></p>` : ''}
                    </div>
                `);
            }
        });
    }

    renderBuildings() {
        if (!this.imdfData.footprints || this.imdfData.footprints.length === 0) {
            console.warn('Нет данных о зданиях');
            return;
        }

        this.imdfData.footprints.forEach(footprint => {
            if (footprint.geometry) {
                L.geoJSON(footprint.geometry, {
                    style: {
                        color: '#6b7280',
                        fillColor: '#f3f4f6',
                        fillOpacity: 0.7,
                        weight: 2
                    }
                }).addTo(this.map).bindPopup(() => {
                    const building = this.getBuildingById(footprint.properties?.building_ids?.[0]);
                    return this.createBuildingPopup(building);
                });
            }
        });
    }

    renderClassrooms() {
        this.clearClassroomLayers();

        const classroomsToShow = this.filterClassroomsByFloor(this.classrooms, this.currentFloor);
        
        console.log('Аудитории для отображения:', classroomsToShow.length);
        
        if (!classroomsToShow || classroomsToShow.length === 0) {
            console.warn('Нет данных об аудиториях для отображения');
            return;
        }

        classroomsToShow.forEach(classroom => {
            if (classroom.unit && classroom.unit.geometry) {
                const color = this.getRoomColor(classroom);
                
                const roomLayer = L.geoJSON(classroom.unit.geometry, {
                    style: {
                        color: color,
                        fillColor: color,
                        fillOpacity: 0.7,
                        weight: 2
                    }
                }).addTo(this.map);

                this.roomLayers.set(classroom.id, roomLayer);

                roomLayer.bindPopup(() => this.createRoomPopup(classroom));

                roomLayer.on('mouseover', function() {
                    this.setStyle({ weight: 4, fillOpacity: 0.9 });
                });
                roomLayer.on('mouseout', function() {
                    this.setStyle({ weight: 2, fillOpacity: 0.7 });
                });
            }else {
            console.warn('Аудитория без геометрии:', classroom.name);
            }
        });

        console.log(`Отображено ${classroomsToShow.length} аудиторий на этаже: ${this.currentFloor}`);
    }

    clearClassroomLayers() {
        this.roomLayers.forEach(layer => {
            this.map.removeLayer(layer);
        });
        this.roomLayers.clear();
    }

    renderOpenings() {
        if (!this.imdfData.openings || this.imdfData.openings.length === 0) {
            console.warn('Нет данных о проходах');
            return;
        }

        this.imdfData.openings.forEach(opening => {
            if (opening.geometry) {
                L.geoJSON(opening.geometry, {
                    style: {
                        color: '#dc2626',
                        weight: 3,
                        opacity: 0.7,
                        dashArray: '5, 5'
                    }
                }).addTo(this.map);
            }
        });
    }

    // Создание попапа для аудитории
    createRoomPopup(classroom) {
        const hasData = (classroom.hasRealData || classroom.co2 !== null) && classroom.co2 !== null;
        
        return `
            <div class="map-popup">
                <h3>${classroom.name}</h3>
                <p><strong>Здание:</strong> ${classroom.buildingName}</p>
                <p><strong>Этаж:</strong> ${classroom.floor}</p>
                
                ${hasData ? `
                    <div class="sensor-data">
                        <p><strong>Данные с датчика:</strong></p>
                        <p>CO₂: ${classroom.co2} ppm</p>
                        <p>Температура: ${classroom.temperature}°C</p>
                        <p>Влажность: ${classroom.humidity}%</p>
                        <p>Качество: ${this.getQualityText(classroom.airQuality)}</p>
                    </div>
                ` : `
                    <p><em>Данные с датчика отсутствуют</em></p>
                `}
                
                <!-- КНОПКА ДЛЯ ПЕРЕХОДА К ГРАФИКАМ -->
                <button onclick="window.showRoomDetails('${classroom.id}')" 
                        class="details-btn">
                    📊 Подробная информация
                </button>
                
                ${classroom.sensorId ? `
                    <p><small>Датчик: ${classroom.sensorId}</small></p>
                ` : ''}
            </div>
        `;
    }

    createBuildingPopup(building) {
        const address = building && building.address_id ? 
            this.getAddressText(building.address_id) : 'Адрес не указан';
        
        return `
            <div class="map-popup">
                <h3>${building ? building.name?.ru || building.name : 'Неизвестное здание'}</h3>
                <p>${address}</p>
            </div>
        `;
    }
    createFloorIndicator() {
        const indicator = L.DomUtil.create('div', 'map-floor-indicator');
        indicator.innerHTML = `
            <i class="fas fa-layer-group"></i>
            <span class="floor-text">Все этажи</span>
        `;
        
        this.map.getContainer().appendChild(indicator);
        this.floorIndicator = indicator;
        
        return indicator;
    }

    createFloorControl() {
        try {
            console.log('Создание контрола этажей...');
            
            // Создаем контейнер для контрола этажей
            const floorControl = L.DomUtil.create('div', 'floor-control');
            floorControl.style.cssText = `
                position: absolute;
                top: 50%;
                left: 20px;
                transform: translateY(-50%);
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                z-index: 1000;
                min-width: 60px;
                max-height: 400px;
                overflow-y: auto;
                padding: 5px 0;
                border: 1px solid #e5e7eb;
                display: flex;
                flex-direction: column;
                align-items: center;
            `;
            
            // Получаем уникальные этажи из аудиторий
            const floors = new Set();
            this.allClassrooms.forEach(classroom => {
                if (classroom.floor) {
                    floors.add(classroom.floor);
                }
            });
            
            // Сортируем этажи в правильном порядке (сверху вниз)
            const sortedFloors = Array.from(floors).sort((a, b) => {
                const order = { 
                    'Цокольный': -1, 
                    'Подвал': -1,
                    '-1': -1,
                    '0': 0,
                    '1': 1, 
                    '2': 2, 
                    '3': 3, 
                    '4': 4, 
                    '5': 5,
                    '6': 6,
                    '7': 7,
                    '8': 8,
                    '9': 9,
                    '10': 10
                };
                
                const aOrder = order[a] !== undefined ? order[a] : parseInt(a);
                const bOrder = order[b] !== undefined ? order[b] : parseInt(b);
                
                return bOrder - aOrder; // Сверху вниз: от верхних этажей к нижним
            });
            
            // Убираем кнопку "Все" и добавляем только этажи
            if (sortedFloors.length === 0) {
                return floorControl;
            }
            
            // Добавляем кнопки для каждого этажа
            sortedFloors.forEach(floor => {
                const button = this.createFloorButton(floor, floor);
                floorControl.appendChild(button);
            });
            
            // Добавляем контейнер на карту
            this.map.getContainer().appendChild(floorControl);
            this.floorControlElement = floorControl;
            
            // Выбираем первый этаж по умолчанию
            const defaultFloor = sortedFloors[sortedFloors.length - 1]; // Берем самый нижний этаж (последний в отсортированном списке)
            this.setFloor(defaultFloor);
            this.selectFloorButton(defaultFloor);
            
            console.log('Контрол этажей создан');
            return floorControl;
            
        } catch (error) {
            console.error('Ошибка создания контрола этажей:', error);
            return null;
        }
    }

    // Метод для создания кнопки этажа
    createFloorButton(label, floorId) {
        const button = L.DomUtil.create('button', 'floor-button');
        button.textContent = label;
        button.dataset.floor = floorId;
        
        button.style.cssText = `
            display: block;
            width: 100%;
            padding: 12px 15px;
            border: none;
            background: white;
            color: #374151;
            font-size: 14px;
            font-weight: 600;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
            border-radius: 0;
            outline: none;
        `;
        
        // Убираем стандартные стили кнопки
        button.style.WebkitAppearance = 'none';
        button.style.MozAppearance = 'none';
        
        // События наведения
        button.onmouseenter = () => {
            if (!button.classList.contains('active')) {
                button.style.background = '#f3f4f6';
            }
        };
        
        button.onmouseleave = () => {
            if (!button.classList.contains('active')) {
                button.style.background = 'white';
            }
        };
        
        // Событие клика
        button.onclick = (e) => {
            e.stopPropagation();
            this.setFloor(floorId);
            this.selectFloorButton(floorId);
        };
        
        return button;
    }

    // Метод для выбора кнопки этажа
    selectFloorButton(floorId) {
        if (!this.floorControlElement) return;
        
        const buttons = this.floorControlElement.querySelectorAll('.floor-button');
        buttons.forEach(button => {
            button.classList.remove('active');
            button.style.background = 'white';
            button.style.color = '#374151';
            button.style.fontWeight = '600';
        });
        
        const activeButton = this.floorControlElement.querySelector(`[data-floor="${floorId}"]`);
        if (activeButton) {
            activeButton.classList.add('active');
            activeButton.style.background = '#3b82f6';
            activeButton.style.color = 'white';
            activeButton.style.fontWeight = '700';
        }
    }

    getRoomColor(classroom) {
        if (!classroom.airQuality) return '#9ca3af';
        
        const colors = {
            excellent: '#10b981',
            good: '#3b82f6',
            fair: '#f59e0b',
            poor: '#ef4444'
        };
        
        return colors[classroom.airQuality] || '#9ca3af';
    }

    getQualityText(quality) {
        const texts = { 
            excellent: "Отличное", 
            good: "Хорошее", 
            fair: "Удовлетворительное", 
            poor: "Плохое" 
        };
        return texts[quality] || "Нет данных";
    }

    getBuildingById(buildingId) {
        return this.imdfData.buildings.find(b => b.id === buildingId);
    }

    getAddressText(addressId) {
        const address = this.imdfData.addresses.find(a => a.id === addressId);
        return address ? `${address.address}, ${address.locality}` : 'Адрес не указан';
    }

    updateLegend(floor) {
        // Удаляем старую легенду, если есть
        if (this.legendControl) {
            this.map.removeControl(this.legendControl);
        }
        
        // Создаем новую легенду
        this.legendControl = L.control({ position: 'bottomright' });
        
        this.legendControl.onAdd = () => {
            const div = L.DomUtil.create('div', 'map-legend');
            div.innerHTML = `
                <h4>Качество воздуха</h4>
                <div class="legend-item">
                    <div class="color-box excellent"></div>
                    <span>Отличное</span>
                </div>
                <div class="legend-item">
                    <div class="color-box good"></div>
                    <span>Хорошее</span>
                </div>
                <div class="legend-item">
                    <div class="color-box fair"></div>
                    <span>Удовлетворительное</span>
                </div>
                <div class="legend-item">
                    <div class="color-box poor"></div>
                    <span>Плохое</span>
                </div>
                <div class="legend-item">
                    <div class="color-box no-data"></div>
                    <span>Нет данных</span>
                </div>
            `;
            return div;
        };
        
        this.legendControl.addTo(this.map);
    }


    addLegend() {
        const legend = L.control({ position: 'bottomright' });

        legend.onAdd = () => {
            const div = L.DomUtil.create('div', 'map-legend');
            div.innerHTML = `
                <h4>Качество воздуха</h4>
                <div class="legend-item">
                    <div class="color-box excellent"></div>
                    <span>Отличное</span>
                </div>
                <div class="legend-item">
                    <div class="color-box good"></div>
                    <span>Хорошее</span>
                </div>
                <div class="legend-item">
                    <div class="color-box fair"></div>
                    <span>Удовлетворительное</span>
                </div>
                <div class="legend-item">
                    <div class="color-box poor"></div>
                    <span>Плохое</span>
                </div>
                <div class="legend-item">
                    <div class="color-box no-data"></div>
                    <span>Нет данных</span>
                </div>
                ${this.currentFloor !== "all" ? `
                <div class="current-floor">
                    <strong>Текущий этаж: ${this.currentFloor}</strong>
                </div>
                ` : ''}
            `;
            return div;
        };

        legend.addTo(this.map);
    }

    updateClassrooms(newClassrooms) {
        this.allClassrooms = newClassrooms;
        this.classrooms = newClassrooms;
        
        // Если контрол этажей уже создан, обновляем его
        if (this.floorControlElement) {
            this.floorControlElement.remove();
            this.createFloorControl();
        }
        
        // Рендерим аудитории текущего этажа
        const filteredClassrooms = this.filterClassroomsByFloor(this.classrooms, this.currentFloor);
        this.clearClassroomLayers();
        
        if (filteredClassrooms && filteredClassrooms.length > 0) {
            filteredClassrooms.forEach(classroom => {
                if (classroom.unit && classroom.unit.geometry) {
                    const color = this.getRoomColor(classroom);
                    
                    const roomLayer = L.geoJSON(classroom.unit.geometry, {
                        style: {
                            color: color,
                            fillColor: color,
                            fillOpacity: 0.7,
                            weight: 2
                        }
                    }).addTo(this.map);

                    this.roomLayers.set(classroom.id, roomLayer);
                    roomLayer.bindPopup(() => this.createRoomPopup(classroom));
                    
                    roomLayer.on('mouseover', function() {
                        this.setStyle({ weight: 4, fillOpacity: 0.9 });
                    });
                    roomLayer.on('mouseout', function() {
                        this.setStyle({ weight: 2, fillOpacity: 0.7 });
                    });
                }
            });
        }
    }

    focusOnRoom(roomId) {
        const classroom = this.classrooms.find(c => c.id === roomId);
        const layer = this.roomLayers.get(roomId);
        
        if (classroom && layer && classroom.unit && classroom.unit.geometry) {
            const geojsonLayer = L.geoJSON(classroom.unit.geometry);
            const bounds = geojsonLayer.getBounds();
            
            this.map.fitBounds(bounds, { padding: [20, 20] });
            layer.openPopup();
        }
    }
}

// Делаем класс доступным глобально
window.CampusMap = CampusMap;