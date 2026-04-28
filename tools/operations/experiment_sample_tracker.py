"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Register and track laboratory experiment samples by recording sample identifiers, storage locations, collection dates, and experimental conditions to maintain chain-of-custody records and enable efficient sample retrieval for downstream analysis."""
    import json
    from datetime import datetime
    
    try:
        data = json.loads(payload)
        
        # Validate required fields
        if 'operation' not in data:
            return json.dumps({'error': 'Missing required field: operation'}, ensure_ascii=False)
        
        operation = data['operation']
        
        # In-memory storage for demonstration (in production, this would use a database)
        sample_storage = {}
        
        if operation == 'create':
            # Validate required fields for create
            required_create = ['sample_id', 'project_name', 'sample_type', 'storage_location', 'collection_date', 'collected_by']
            missing = [f for f in required_create if f not in data]
            if missing:
                return json.dumps({'error': f'Missing required fields for create: {missing}'}, ensure_ascii=False)
            
            # Validate date format
            try:
                datetime.strptime(data['collection_date'], '%Y-%m-%d')
            except ValueError:
                return json.dumps({'error': 'collection_date must be in YYYY-MM-DD format'}, ensure_ascii=False)
            
            # Validate sample_type
            valid_types = ['tissue', 'blood', 'soil', 'water', 'cell_culture', 'protein_extract', 'nucleic_acid', 'other']
            if data['sample_type'] not in valid_types:
                return json.dumps({'error': f'Invalid sample_type. Must be one of: {valid_types}'}, ensure_ascii=False)
            
            # Check for duplicate sample_id
            if data['sample_id'] in sample_storage:
                return json.dumps({'error': f'Sample with ID {data["sample_id"]} already exists'}, ensure_ascii=False)
            
            sample_record = {
                'sample_id': data['sample_id'],
                'project_name': data['project_name'],
                'sample_type': data['sample_type'],
                'storage_location': data['storage_location'],
                'collection_date': data['collection_date'],
                'collected_by': data['collected_by'],
                'experimental_conditions': data.get('experimental_conditions', ''),
                'notes': data.get('notes', ''),
                'status': 'active',
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
            sample_storage[data['sample_id']] = sample_record
            return json.dumps({'message': 'Sample created successfully', 'sample': sample_record}, ensure_ascii=False)
        
        elif operation == 'update':
            if 'sample_id' not in data:
                return json.dumps({'error': 'sample_id is required for update operation'}, ensure_ascii=False)
            if data['sample_id'] not in sample_storage:
                return json.dumps({'error': f'Sample with ID {data["sample_id"]} not found'}, ensure_ascii=False)
            
            sample = sample_storage[data['sample_id']]
            updatable_fields = ['storage_location', 'experimental_conditions', 'notes', 'status']
            for field in updatable_fields:
                if field in data:
                    if field == 'status':
                        valid_statuses = ['active', 'consumed', 'degraded', 'discarded', 'transferred']
                        if data['status'] not in valid_statuses:
                            return json.dumps({'error': f'Invalid status. Must be one of: {valid_statuses}'}, ensure_ascii=False)
                    sample[field] = data[field]
            sample['last_updated'] = datetime.now().isoformat()
            sample_storage[data['sample_id']] = sample
            return json.dumps({'message': 'Sample updated successfully', 'sample': sample}, ensure_ascii=False)
        
        elif operation == 'retrieve':
            if 'sample_id' not in data:
                return json.dumps({'error': 'sample_id is required for retrieve operation'}, ensure_ascii=False)
            if data['sample_id'] not in sample_storage:
                return json.dumps({'error': f'Sample with ID {data["sample_id"]} not found'}, ensure_ascii=False)
            return json.dumps({'sample': sample_storage[data['sample_id']]}, ensure_ascii=False)
        
        elif operation == 'list':
            project_filter = data.get('project_name', '')
            if project_filter:
                matching_samples = [s for s in sample_storage.values() if s['project_name'] == project_filter]
            else:
                matching_samples = list(sample_storage.values())
            return json.dumps({'total_samples': len(matching_samples), 'samples': matching_samples}, ensure_ascii=False)
        
        else:
            return json.dumps({'error': f'Invalid operation: {operation}. Must be one of: create, update, retrieve, list'}, ensure_ascii=False)
            
    except json.JSONDecodeError as e:
        return json.dumps({'error': f'Invalid JSON payload: {str(e)}'}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({'error': f'Unexpected error: {str(e)}'}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "experiment_sample_tracker",
    "description": "Register and track laboratory experiment samples by recording sample identifiers, storage locations, collection dates, and experimental conditions to maintain chain-of-custody records and enable efficient sample retrieval for downstream analysis.",
    "category": "operations",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "description": "Action to perform on sample records: create new sample, update existing sample, retrieve sample details, or list samples by project",
            "enum": [
                "create",
                "update",
                "retrieve",
                "list"
            ]
        },
        "sample_id": {
            "type": "string",
            "description": "Unique alphanumeric identifier for the experiment sample (e.g., EXP-2024-001-A12); used for update, retrieve, and list operations"
        },
        "project_name": {
            "type": "string",
            "description": "Name of the research project the sample belongs to, for grouping and filtering samples"
        },
        "sample_type": {
            "type": "string",
            "description": "Type of sample material: tissue, blood, soil, water, cell_culture, protein_extract, nucleic_acid, or other",
            "enum": [
                "tissue",
                "blood",
                "soil",
                "water",
                "cell_culture",
                "protein_extract",
                "nucleic_acid",
                "other"
            ]
        },
        "storage_location": {
            "type": "string",
            "description": "Physical storage location identifier including freezer/rack/box/position (e.g., Freezer-03, Rack-B2, Box-07, Pos-14)"
        },
        "collection_date": {
            "type": "string",
            "description": "Date when the sample was collected or generated, in ISO 8601 format (YYYY-MM-DD)"
        },
        "collected_by": {
            "type": "string",
            "description": "Name or identifier of the person who collected the sample"
        },
        "experimental_conditions": {
            "type": "string",
            "description": "Optional: Description of relevant experimental conditions at time of collection (temperature, pH, treatment, timepoint, etc.)"
        },
        "notes": {
            "type": "string",
            "description": "Optional: Additional notes or observations about the sample"
        },
        "status": {
            "type": "string",
            "description": "Optional: Current status of the sample for update operations: active, consumed, degraded, discarded, or transferred",
            "enum": [
                "active",
                "consumed",
                "degraded",
                "discarded",
                "transferred"
            ]
        }
    },
    "required": [
        "operation"
    ]
},
}
