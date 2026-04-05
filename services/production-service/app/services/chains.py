"""Production chain service - dependency tree analysis."""
import logging
from typing import Dict, List, Optional, Any
import math

from app.models import ProductionChainNode
from app.services.repository import ProductionRepository

logger = logging.getLogger(__name__)


class ProductionChainService:
    """Service for analyzing production dependency chains."""

    def __init__(self, db):
        """Initialize with database pool."""
        self.repository = ProductionRepository(db)
        self._cache: Dict[int, ProductionChainNode] = {}

    def get_chain_tree(
        self,
        type_id: int,
        quantity: int = 1,
        format: str = "tree"
    ) -> Dict[str, Any]:
        """
        Get complete production chain for an item.

        Args:
            type_id: Item type ID
            quantity: Quantity to produce
            format: 'tree' for hierarchical, 'flat' for simple list

        Returns:
            Production chain data
        """
        name = self.repository.get_item_name(type_id)
        if not name:
            return {"error": f"Item not found: {type_id}"}

        # Build tree recursively
        root = self._build_tree(type_id, quantity, visited=set())

        if format == "flat":
            flat_materials = {}
            self._flatten_tree(root, flat_materials)
            return {
                "type_id": type_id,
                "name": name,
                "quantity": quantity,
                "materials": [
                    {"type_id": tid, "name": data["name"], "quantity": data["quantity"]}
                    for tid, data in flat_materials.items()
                ]
            }

        return {
            "type_id": type_id,
            "name": name,
            "quantity": quantity,
            "chain": self._node_to_dict(root)
        }

    def _build_tree(
        self,
        type_id: int,
        quantity: int,
        visited: set
    ) -> ProductionChainNode:
        """Build production chain tree recursively."""
        name = self.repository.get_item_name(type_id) or "Unknown"
        is_manufacturable = self.repository.is_manufacturable(type_id)

        node = ProductionChainNode(
            type_id=type_id,
            name=name,
            quantity=quantity,
            is_manufacturable=is_manufacturable,
            children=[]
        )

        # Prevent infinite recursion
        if type_id in visited:
            return node

        if is_manufacturable:
            visited.add(type_id)

            blueprint_id = self.repository.get_blueprint_for_product(type_id)
            if blueprint_id:
                materials = self.repository.get_blueprint_materials(blueprint_id)
                output_per_run = self.repository.get_output_quantity(blueprint_id, type_id)

                # Calculate runs needed
                runs_needed = math.ceil(quantity / output_per_run) if output_per_run > 0 else quantity

                for material_id, base_qty in materials:
                    # Calculate total quantity needed
                    mat_qty = base_qty * runs_needed
                    child = self._build_tree(material_id, mat_qty, visited.copy())
                    node.children.append(child)

        return node

    def _flatten_tree(
        self,
        node: ProductionChainNode,
        result: Dict[int, Dict[str, Any]]
    ):
        """Flatten tree into material list."""
        if not node.is_manufacturable or not node.children:
            # Leaf node - add to result
            if node.type_id in result:
                result[node.type_id]["quantity"] += node.quantity
            else:
                result[node.type_id] = {
                    "name": node.name,
                    "quantity": node.quantity
                }
        else:
            # Has children - recurse
            for child in node.children:
                self._flatten_tree(child, result)

    def _node_to_dict(self, node: ProductionChainNode) -> Dict[str, Any]:
        """Convert node to dict for JSON response."""
        return {
            "type_id": node.type_id,
            "name": node.name,
            "quantity": node.quantity,
            "is_manufacturable": node.is_manufacturable,
            "children": [self._node_to_dict(c) for c in node.children]
        }

    def get_materials_list(
        self,
        type_id: int,
        me: int = 0,
        runs: int = 1
    ) -> Dict[str, Any]:
        """
        Get flattened material list with ME adjustments.

        Args:
            type_id: Item type ID
            me: Material Efficiency level (0-10)
            runs: Number of production runs

        Returns:
            Material list with quantities
        """
        name = self.repository.get_item_name(type_id)
        if not name:
            return {"error": f"Item not found: {type_id}"}

        blueprint_id = self.repository.get_blueprint_for_product(type_id)
        if not blueprint_id:
            return {"error": f"No blueprint found for: {name}"}

        materials = self.repository.get_blueprint_materials(blueprint_id)
        me_factor = 1 - (me / 100)

        result = []
        for material_id, base_qty in materials:
            mat_name = self.repository.get_item_name(material_id) or "Unknown"
            adjusted_qty = max(1, math.ceil(base_qty * me_factor)) * runs

            result.append({
                "type_id": material_id,
                "name": mat_name,
                "base_quantity": base_qty,
                "adjusted_quantity": adjusted_qty,
                "per_run": max(1, math.ceil(base_qty * me_factor))
            })

        return {
            "type_id": type_id,
            "name": name,
            "me": me,
            "runs": runs,
            "materials": result
        }

    def get_direct_dependencies(self, type_id: int) -> Dict[str, Any]:
        """Get only direct material dependencies (1 level)."""
        name = self.repository.get_item_name(type_id)
        if not name:
            return {"error": f"Item not found: {type_id}"}

        blueprint_id = self.repository.get_blueprint_for_product(type_id)
        if not blueprint_id:
            return {"error": f"No blueprint found for: {name}"}

        materials = self.repository.get_blueprint_materials(blueprint_id)

        result = []
        for material_id, quantity in materials:
            mat_name = self.repository.get_item_name(material_id) or "Unknown"
            is_manufacturable = self.repository.is_manufacturable(material_id)

            result.append({
                "type_id": material_id,
                "name": mat_name,
                "quantity": quantity,
                "is_manufacturable": is_manufacturable
            })

        return {
            "type_id": type_id,
            "name": name,
            "materials": result
        }
