import React from 'react';
import { tokens } from '../styles/tokens';

type CardProps = {
  title?: string;
  children: React.ReactNode;
  className?: string;
};

export const Card: React.FC<CardProps> = ({ title, children, className }) => {
  return (
    <section className={`dashboard-card ${className ?? ''}`} style={{ borderRadius: 12 }}>
      {title ? <div className="card-title">{title}</div> : null}
      <div style={{ padding: 4 }}>{children}</div>
    </section>
  );
};

export default Card;
