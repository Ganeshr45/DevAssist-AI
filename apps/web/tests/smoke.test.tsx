import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import Home from '../app/page';

describe('landing page', () => {
  it('introduces the developer support workspace and exposes primary navigation', () => {
    render(<Home />);
    expect(screen.getByRole('heading', { name: /make the hard parts clear/i })).toBeTruthy();
    expect(screen.getByRole('link', { name: /open assistant/i })).toBeTruthy();
    expect(screen.getByRole('link', { name: /explore knowledge base/i })).toBeTruthy();
  });
});
