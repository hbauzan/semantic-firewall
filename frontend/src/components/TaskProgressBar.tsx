import React from 'react';

interface TaskProgressBarProps {
  progress: number | null;
  stalled?: boolean;
  className?: string;
}

/** Determinate bar (0–100) or animated indeterminate strip when progress is null. */
export const TaskProgressBar: React.FC<TaskProgressBarProps> = ({
  progress,
  stalled = false,
  className = '',
}) => {
  const indeterminate = progress === null;
  const width = indeterminate ? undefined : `${Math.min(100, Math.max(0, progress))}%`;

  return (
    <div className={`task-progress ${stalled ? 'task-progress--stalled' : ''} ${className}`.trim()}>
      <div className="task-progress-track">
        <div
          className={`task-progress-fill ${indeterminate ? 'task-progress-fill--indeterminate' : ''}`}
          style={width ? { width } : undefined}
        />
      </div>
    </div>
  );
};
