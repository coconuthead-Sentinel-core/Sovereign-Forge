# tests/test_quantum_nexus.py
"""Tests for the Quantum Nexus lattice coordinate system."""
import pytest
from backend.services.quantum_nexus import QuantumNexus, GreatGreg


# Sample blueprint for testing
SAMPLE_BLUEPRINT = {
    "great_greg_coordinates": {
        "rc_map": {
            "A1": {"r": 1, "c": 1, "node": 1, "label": "Fluent Python"},
            "B1": {"r": 1, "c": 2, "node": 1, "label": "Deep Learning with Python"},
            "H1": {"r": 2, "c": 2, "node": 2, "label": "Symbol Registry (1)"},
            "O1": {"r": 3, "c": 3, "node": 3, "label": "GitHub Essentials"},
            "P1": {"r": 3, "c": 4, "node": 3, "label": "Prompt Engineering Workshop"},
            "V1": {"r": 4, "c": 4, "node": 4, "label": "AI Mind Map Generation"},
            "Z1": {"r": 5, "c": 2, "node": 5, "label": "ZA1 Dynamic Expansion (Future Modules)"},
        }
    },
    "nodes": [
        {"id": "Node_1_Technical_Arsenal", "color": "yellow", "cells": ["A1", "B1"]},
        {"id": "Node_3_Skill_Forge", "color": "green", "cells": ["O1", "P1"]},
    ],
    "dependencies": [
        {
            "id": "dep_A1_to_V1",
            "type": "diagonal_dependency",
            "from": "A1",
            "to": "V1",
            "path": ["A1", "H1", "O1", "V1"],
        },
        {
            "id": "dep_AllFiles_L2R_to_Z1",
            "type": "lateral_row_major_dependency",
            "from": "A1",
            "to": "Z1",
            "path": [
                ["A1", "B1"],
                ["H1"],
                ["O1", "P1"],
                ["V1"],
                ["Z1"],
            ],
        },
    ],
}


@pytest.fixture
def nexus():
    """Create a QuantumNexus instance from sample blueprint."""
    return QuantumNexus.from_dict(SAMPLE_BLUEPRINT)


class TestGreatGregResolver:
    """Tests for Great Greg coordinate resolution."""

    def test_resolve_cell_direct(self, nexus):
        """Test direct cell resolution (e.g., 'P1')."""
        coord = nexus.resolve("P1")
        assert coord.cell == "P1"
        assert coord.r == 3
        assert coord.c == 4
        assert coord.node == 3
        assert coord.label == "Prompt Engineering Workshop"

    def test_resolve_cell_with_node_prefix(self, nexus):
        """Test node-prefixed cell resolution (e.g., 'Node_3:P1')."""
        coord = nexus.resolve("Node_3:P1")
        assert coord.cell == "P1"
        assert coord.r == 3
        assert coord.c == 4
        assert coord.node == 3

    def test_resolve_rc_format(self, nexus):
        """Test row/column/node triplet resolution (e.g., 'Node_3.R3C4')."""
        coord = nexus.resolve("Node_3.R3C4")
        assert coord.cell == "P1"
        assert coord.r == 3
        assert coord.c == 4
        assert coord.node == 3

    def test_resolve_origin(self, nexus):
        """Test origin cell (A1 - Prime Truth)."""
        origin = nexus.origin
        assert origin.cell == "A1"
        assert origin.r == 1
        assert origin.c == 1
        assert origin.node == 1

    def test_resolve_terminus(self, nexus):
        """Test terminus cell (Z1 - Dynamic Expansion)."""
        terminus = nexus.terminus
        assert terminus.cell == "Z1"
        assert terminus.r == 5
        assert terminus.c == 2
        assert terminus.node == 5

    def test_unknown_cell_raises(self, nexus):
        """Test that unknown cell raises KeyError."""
        with pytest.raises(KeyError, match="Unknown cell"):
            nexus.resolve("ZZ99")

    def test_case_insensitive(self, nexus):
        """Test that cell resolution is case-insensitive."""
        coord = nexus.resolve("p1")
        assert coord.cell == "P1"


class TestDependencyLookup:
    """Tests for dependency lookup and tracing."""

    def test_get_diagonal_dependency(self, nexus):
        """Test retrieving the diagonal dependency."""
        dep = nexus.dependency("dep_A1_to_V1")
        assert dep["type"] == "diagonal_dependency"
        assert dep["from"] == "A1"
        assert dep["to"] == "V1"

    def test_get_lateral_dependency(self, nexus):
        """Test retrieving the lateral row-major dependency."""
        dep = nexus.dependency("dep_AllFiles_L2R_to_Z1")
        assert dep["type"] == "lateral_row_major_dependency"
        assert dep["from"] == "A1"
        assert dep["to"] == "Z1"

    def test_unknown_dependency_raises(self, nexus):
        """Test that unknown dependency raises KeyError."""
        with pytest.raises(KeyError, match="Dependency not found"):
            nexus.dependency("dep_unknown")

    def test_trace_diagonal_path(self, nexus):
        """Test tracing the diagonal dependency path."""
        path = nexus.diagonal_trace()
        assert len(path) == 4
        assert path[0].cell == "A1"
        assert path[1].cell == "H1"
        assert path[2].cell == "O1"
        assert path[3].cell == "V1"

    def test_trace_lateral_path(self, nexus):
        """Test tracing the lateral row-major path."""
        path = nexus.lateral_trace()
        cells = [p.cell for p in path]
        assert "A1" in cells
        assert "Z1" in cells
        assert cells[0] == "A1"  # Origin first
        assert cells[-1] == "Z1"  # Terminus last


class TestNodeLookup:
    """Tests for node lookup."""

    def test_get_node(self, nexus):
        """Test retrieving a node by ID."""
        node = nexus.node("Node_1_Technical_Arsenal")
        assert node["color"] == "yellow"
        assert "A1" in node["cells"]

    def test_get_node_cells(self, nexus):
        """Test getting all cells for a node."""
        cells = nexus.get_node_cells("Node_3_Skill_Forge")
        assert len(cells) == 2
        cell_names = [c.cell for c in cells]
        assert "O1" in cell_names
        assert "P1" in cell_names

    def test_unknown_node_raises(self, nexus):
        """Test that unknown node raises KeyError."""
        with pytest.raises(KeyError, match="Node not found"):
            nexus.node("Node_99_Unknown")


class TestAPIResponse:
    """Tests for API response formatting."""

    def test_to_api_response(self, nexus):
        """Test converting coordinate to API response format."""
        response = nexus.to_api_response("P1")
        assert response["cell"] == "P1"
        assert response["row"] == 3
        assert response["column"] == 4
        assert response["node"] == 3
        assert response["node_id"] == "Node_3"
        assert response["label"] == "Prompt Engineering Workshop"


class TestGreatGregDataclass:
    """Tests for the GreatGreg dataclass."""

    def test_immutable(self):
        """Test that GreatGreg is immutable (frozen)."""
        coord = GreatGreg(cell="A1", r=1, c=1, node=1, label="Test")
        with pytest.raises(AttributeError):
            coord.cell = "B1"

    def test_equality(self):
        """Test GreatGreg equality."""
        coord1 = GreatGreg(cell="A1", r=1, c=1, node=1, label="Test")
        coord2 = GreatGreg(cell="A1", r=1, c=1, node=1, label="Test")
        assert coord1 == coord2

    def test_hashable(self):
        """Test that GreatGreg is hashable (can be used in sets/dicts)."""
        coord = GreatGreg(cell="A1", r=1, c=1, node=1, label="Test")
        coord_set = {coord}
        assert coord in coord_set
