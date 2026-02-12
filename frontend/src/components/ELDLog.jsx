import React, { useEffect, useRef, useState } from 'react';

const DayLog = ({ segments, dayIndex }) => {
    const canvasRef = useRef(null);
    const [hoveredInfo, setHoveredInfo] = useState(null);

    // Constants (Must match drawing logic)
    const height = 200;
    const gridTop = 30;
    const gridHeight = height - gridTop - 20;
    const rowH = gridHeight / 4;
    const labelWidth = 80;

    // We can't know width until mount usually, but we set it to 800 fixed in render for now, or use resize observer.
    // The previous code had `canvas width={800}`.
    const width = 800;
    const chartWidth = width - labelWidth - 20;
    const pixelsPerHour = chartWidth / 24;

    const handleMouseMove = (e) => {
        const rect = canvasRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Determine Time
        if (x < labelWidth) {
            setHoveredInfo(null);
            return;
        }

        const timePx = x - labelWidth;
        const hour = timePx / pixelsPerHour; // hours since midnight of this day
        const maxHour = 24.0;

        if (hour < 0 || hour > maxHour) {
            setHoveredInfo(null);
            return;
        }

        const absTime = (dayIndex * 24) + hour;

        // Find Segment
        // Segments are sorted by start_time usually.
        const segment = segments.find(seg => {
            const start = seg.start_time;
            const end = seg.start_time + seg.duration;
            return absTime >= start && absTime < end;
        });

        if (segment) {
            setHoveredInfo({
                x: e.clientX,
                y: e.clientY,
                segment: segment
            });
        } else {
            setHoveredInfo(null);
        }
    };

    const handleMouseLeave = () => {
        setHoveredInfo(null);
    };

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        // width/height from props/ref
        // Ensure canvas internal size matches
        canvas.width = width;
        canvas.height = height;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        // Configuration
        const labels = ['Off Duty', 'Sleeper', 'Driving', 'On Duty'];
        const colors = {
            'off_duty': '#212121', // Black/Dark Grey
            'sleeper': '#1976D2', // Blue
            'driving': '#388E3C', // Green
            'on_duty': '#FBC02D'  // Yellow
        };

        // Draw Labels & Grid Rows
        ctx.font = '12px Inter, sans-serif';
        ctx.textBaseline = 'middle';

        labels.forEach((label, i) => {
            const y = gridTop + (i * rowH);

            // Text Label
            ctx.fillStyle = '#333';
            ctx.textAlign = 'right';
            ctx.fillText(label, labelWidth - 10, y + rowH / 2);

            // Row Box
            ctx.strokeStyle = '#e0e0e0';
            ctx.strokeRect(labelWidth, y, chartWidth, rowH);
        });

        // Draw Time Markers (Vertical Lines)
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        for (let h = 0; h <= 24; h++) {
            const x = labelWidth + (h * pixelsPerHour);

            // Line
            ctx.strokeStyle = h % 3 === 0 ? '#999' : '#eee'; // Major/Minor lines
            ctx.beginPath();
            ctx.moveTo(x, gridTop);
            ctx.lineTo(x, gridTop + gridHeight);
            ctx.stroke();

            // Time Text (Midnight, 3am, 6am...) at top
            if (h % 3 === 0) {
                let time = h === 0 || h === 24 ? 'M' : (h > 12 ? h - 12 : h);
                ctx.fillText(time.toString(), x, gridTop - 5);
            }
        }

        // Filter segments for this specific day (dayIndex)
        // A day is from hour dayIndex*24 to (dayIndex+1)*24
        const dayStart = dayIndex * 24;
        const dayEnd = (dayIndex + 1) * 24;

        segments.forEach(seg => {
            const segStart = seg.start_time;
            const segEnd = seg.start_time + seg.duration;

            // Check overlap with this day
            if (segEnd <= dayStart || segStart >= dayEnd) return;

            // Clip to this day
            const visibleStart = Math.max(segStart, dayStart);
            const visibleEnd = Math.min(segEnd, dayEnd);
            const duration = visibleEnd - visibleStart;

            // Map Status to Row
            let status = seg.status || seg.type; // backend uses 'type'/'status'
            if (status === 'sleeper_berth') status = 'sleeper';

            const rowMap = {
                'off_duty': 0, 'sleeper': 1, 'driving': 2, 'on_duty': 3
            };
            const row = rowMap[status] !== undefined ? rowMap[status] : 3;

            // Draw Bar
            const x = labelWidth + ((visibleStart - dayStart) * pixelsPerHour);
            const y = gridTop + (row * rowH) + 5; // 5px padding
            const w = duration * pixelsPerHour;
            const h = rowH - 10;

            ctx.fillStyle = colors[status] || '#999';
            ctx.fillRect(x, y, w, h);
        });
    }, [segments, dayIndex]);

    return (
        <div className="day-log-wrapper" style={{ marginBottom: '2rem', position: 'relative' }}>
            <h3>Day {dayIndex + 1}</h3>
            <canvas
                ref={canvasRef}
                width={800}
                height={200}
                style={{ width: '100%', border: '1px solid #ddd', cursor: 'crosshair' }}
                onMouseMove={handleMouseMove}
                onMouseLeave={handleMouseLeave}
            />
            {hoveredInfo && (
                <div style={{
                    position: 'fixed',
                    top: hoveredInfo.y + 10,
                    left: hoveredInfo.x + 10,
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    color: '#fff',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    pointerEvents: 'none',
                    zIndex: 1000
                }}>
                    <div style={{ fontWeight: 'bold' }}>{hoveredInfo.segment.description}</div>
                    <div>Duration: {hoveredInfo.segment.duration.toFixed(2)} hrs</div>
                    <div>Type: {hoveredInfo.segment.type}</div>
                </div>
            )}
        </div>
    );
};

const ELDLog = ({ segments }) => {
    if (!segments || segments.length === 0) return null;

    // Determine number of days
    const totalDuration = segments[segments.length - 1].start_time + segments[segments.length - 1].duration;
    const numDays = Math.ceil(totalDuration / 24) || 1;

    // Create an array of days
    const days = Array.from({ length: numDays }, (_, i) => i);

    return (
        <div className="eld-log-container card">
            <h2>ELD Logs</h2>
            {days.map(dayIndex => (
                <DayLog key={dayIndex} segments={segments} dayIndex={dayIndex} />
            ))}
        </div>
    );
};

export default ELDLog;
