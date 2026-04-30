import React from "react";
import "../styles/components/TrackingToggle.css";

interface TrackingToggleProps {
  isTracking: boolean;
  onToggle: (value: boolean) => void;
}

const TrackingToggle: React.FC<TrackingToggleProps> = ({
  isTracking,
  onToggle,
}) => {
  return (
    <div className="tracking-toggle-wrapper">
      <label className="tracking-label">
        {isTracking ? "Tracking..." : "Start Tracking!"}
      </label>
      <div className="toggle-switch">
        <input
          type="checkbox"
          id="tracking-toggle"
          className="toggle-checkbox"
          checked={isTracking}
          onChange={(e) => onToggle(e.target.checked)}
        />
        <label htmlFor="tracking-toggle" className="toggle-label">
          <span className="toggle-slider" />
        </label>
      </div>
    </div>
  );
};

export default TrackingToggle;
