from models.product import AttributeStatus, AttributeValue, SourceType
from models.state import ProductIdentity, ProductState


def test_attribute_value_defaults():
    attr = AttributeValue(value=5.5, unit="kW")
    assert attr.confidence == 0.5
    assert attr.status == AttributeStatus.EXTRACTED


def test_product_state_to_final_json_shape():
    state = ProductState(
        product_identity=ProductIdentity(part_number="X200", brand="ABC Industries", description="pump")
    )
    state.attributes["power"] = AttributeValue(
        value=5.5, unit="kW", confidence=0.96, source="datasheet.pdf", source_type=SourceType.PDF
    )
    record = state.to_final_json()
    assert record["manufacturer"] == "ABC Industries"
    assert "power" in record["attributes"]
    assert record["attributes"]["power"]["value"] == 5.5


def test_processing_log():
    state = ProductState(
        product_identity=ProductIdentity(part_number="X200", brand="ABC Industries", description="pump")
    )
    state.log("discovery_agent", "completed", "3 attributes")
    assert len(state.processing_log) == 1
    assert state.processing_log[0].agent == "discovery_agent"
