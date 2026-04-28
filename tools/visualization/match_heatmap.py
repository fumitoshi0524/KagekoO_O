"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a positional heatmap visualization for player movement analysis."""
    import json
    import math
    try:
        data = json.loads(payload)
        
        # Validate required fields
        required = ['player_id', 'match_id', 'positions']
        for field in required:
            if field not in data or data[field] is None:
                return f'error: Missing required field "{field}"'
        
        player_id = data['player_id']
        match_id = data['match_id']
        positions = data['positions']
        
        # Validate positions
        if not isinstance(positions, list) or len(positions) < 1:
            return 'error: positions must be a non-empty array'
        for pos in positions:
            if not isinstance(pos, list) or len(pos) != 2:
                return 'error: each position must be an array of [x, y]'
            if not all(isinstance(v, (int, float)) and 0 <= v <= 100 for v in pos):
                return 'error: position values must be numbers between 0 and 100'
        
        # Get optional parameters
        resolution = data.get('resolution', 20)
        resolution = max(10, min(100, int(resolution)))
        
        blur_radius = data.get('blur_radius', 1.5)
        blur_radius = max(0.5, min(5.0, float(blur_radius)))
        
        # Create grid
        grid_size = resolution
        grid = [[0 for _ in range(grid_size)] for _ in range(grid_size)]
        
        # Map positions to grid cells
        scale = grid_size / 100.0
        for pos in positions:
            x, y = pos
            grid_x = min(int(x * scale), grid_size - 1)
            grid_y = min(int(y * scale), grid_size - 1)
            grid[grid_y][grid_x] += 1
        
        # Apply Gaussian blur
        kernel_size = int(blur_radius * 2)
        if kernel_size % 2 == 0:
            kernel_size += 1
        half_kernel = kernel_size // 2
        
        sigma = blur_radius
        kernel = []
        kernel_sum = 0
        for i in range(-half_kernel, half_kernel + 1):
            for j in range(-half_kernel, half_kernel + 1):
                value = math.exp(-(i*i + j*j) / (2 * sigma * sigma))
                kernel.append(value)
                kernel_sum += value
        kernel = [v / kernel_sum for v in kernel]
        
        temp_grid = [[0 for _ in range(grid_size)] for _ in range(grid_size)]
        for y in range(grid_size):
            for x in range(grid_size):
                total = 0.0
                kernel_idx = 0
                for dy in range(-half_kernel, half_kernel + 1):
                    for dx in range(-half_kernel, half_kernel + 1):
                        nx = x + dx
                        ny = y + dy
                        if 0 <= nx < grid_size and 0 <= ny < grid_size:
                            total += grid[ny][nx] * kernel[kernel_idx]
                        kernel_idx += 1
                temp_grid[y][x] = total
        
        # Normalize to 0-100 range for visualization
        max_val = max(max(row) for row in temp_grid)
        if max_val > 0:
            normalized_grid = [[min(100, int((v / max_val) * 100)) for v in row] for row in temp_grid]
        else:
            normalized_grid = [[0 for _ in range(grid_size)] for _ in range(grid_size)]
        
        # Prepare result
        result = {
            'heatmap': {
                'player_id': player_id,
                'match_id': match_id,
                'grid_size': grid_size,
                'grid_data': normalized_grid,
                'total_positions': len(positions),
                'max_density': max_val
            },
            'summary': {
                'most_active_zone': None,
                'zone_coverage_percentage': 0.0
            }
        }
        
        # Calculate summary statistics
        active_cells = sum(1 for row in normalized_grid for v in row if v > 0)
        total_cells = grid_size * grid_size
        coverage = round((active_cells / total_cells) * 100, 1)
        result['summary']['zone_coverage_percentage'] = coverage
        
        # Find most active zone
        max_val = 0
        max_zone = [0, 0]
        for y in range(grid_size):
            for x in range(grid_size):
                if normalized_grid[y][x] > max_val:
                    max_val = normalized_grid[y][x]
                    max_zone = [x, y]
        result['summary']['most_active_zone'] = {
            'grid_x': max_zone[0],
            'grid_y': max_zone[1],
            'pitch_x': round(max_zone[0] * (100 / grid_size), 1),
            'pitch_y': round(max_zone[1] * (100 / grid_size), 1),
            'intensity': max_val
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except json.JSONDecodeError as e:
        return f'error: Invalid JSON payload - {str(e)}'
    except Exception as e:
        return f'error: {str(e)}'


TOOL_SPEC = {
    "name": "match_heatmap",
    "description": "Generate an interactive heatmap visualization of player positioning and movement density during a sports match, using timestamped coordinate data to create a positional frequency chart for tactical analysis.",
    "category": "visualization",
    "domain": "sports",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "player_id": {
            "type": "string",
            "description": "Unique identifier for the player whose movement data will be visualized"
        },
        "match_id": {
            "type": "string",
            "description": "Unique identifier for the match or game session"
        },
        "positions": {
            "type": "array",
            "description": "Array of x,y coordinate arrays representing player position at each timestamp (pitch mapped as 0-100 for x and y axes)",
            "items": {
                "type": "array",
                "items": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100
                },
                "minItems": 2,
                "maxItems": 2
            }
        },
        "resolution": {
            "type": "integer",
            "description": "Optional: Grid resolution for the heatmap (number of cells per axis). Higher values give more granular detail. Range: 10-100, default: 20",
            "default": 20,
            "minimum": 10,
            "maximum": 100
        },
        "blur_radius": {
            "type": "number",
            "description": "Optional: Gaussian blur radius applied to heatmap for smoothing. Range: 0.5-5.0, default: 1.5",
            "default": 1.5,
            "minimum": 0.5,
            "maximum": 5.0
        }
    },
    "required": [
        "player_id",
        "match_id",
        "positions"
    ]
},
}
