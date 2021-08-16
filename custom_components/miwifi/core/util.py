from homeassistant.util import slugify

def _generate_entity_id(
    entity_id_format: str,
    name: str
) -> str:
    name = name.lower()
    preferred_string = entity_id_format.format(slugify(name))

    return preferred_string