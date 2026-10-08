"""Review every EAV candidate; evidence gaps stay explicit, never silently excluded."""
import collections
import copy
import hashlib
import json
import pathlib
from urllib.parse import unquote, urlsplit

ROOT = pathlib.Path(__file__).resolve().parent


def read(path):
    return json.loads(pathlib.Path(path).read_text(encoding='utf-8-sig'))


def image_match(witness, urls, values):
    identity = next((r['entity_id'] for r in urls
                     if r['entity_type'] == 'product' and
                     r['request_path'] == urlsplit(witness['url']).path.lstrip('/')), None)
    for index, record in enumerate(values):
        value = record['value']
        if record['entity_id'] != identity or record['attribute_code'] != 'image':
            continue
        if not value or value == 'no_selection':
            continue
        for ref in witness['evidence_refs']:
            parsed = urlsplit(str(ref['quote']))
            if parsed.scheme in ('http', 'https') and unquote(parsed.path).endswith('/' + value.lstrip('/')):
                return {'pointer': f'/data/product_varchar/{index}', 'value': record,
                        'ui_ref': ref, 'note': 'Same product and image resource path; image content not verified'}
    return None


def main():
    old = read(ROOT / 'db-ui-mapping.v1.json')
    result = copy.deepcopy(old)
    exported = read(ROOT / 'db-export.v2.json')['data']
    audit = read(ROOT / 'db-frontend-audit.20261008.json')
    samples = read(ROOT / 'db-public-samples.20261008.json')['data']
    image = next(r for r in result['facts'] if r['fact_id'] == 'product.image')
    match = image_match(image['ui_witness'], exported['urls'], exported['product_varchar'])
    if not match:
        raise RuntimeError('Image mapping requires same-product resource witness')
    image.update(status='matched_same_product_image_resource', physical_key='product.image',
                 storage='catalog_product_entity_varchar.value / image', db_refs=[match])
    metadata = {(r['entity_type_code'], r['attribute_code']): (i, r)
                for i, r in enumerate(audit['data']['frontend_metadata'])}
    navigation = {'path', 'position', 'all_children', 'path_in_store', 'children', 'level',
                  'children_count', 'available_sort_by', 'default_sort_by', 'include_in_menu',
                  'filter_price_range', 'url_key', 'url_path', 'category_ids', 'is_active', 'is_anchor'}
    configuration = {'options_container', 'required_options', 'has_options',
                     'msrp_display_actual_price_type', 'links_purchased_separately', 'links_exist',
                     'price_type', 'sku_type', 'weight_type', 'price_view', 'shipment_type',
                     'gift_message_available', 'tax_class_id'}
    for row in result['eav_candidates']:
        ent, code = row['entity'], row['attribute']
        key = ('product' if ent == 'catalog_product' else 'category') + '.' + code
        ids = [f['fact_id'] for f in result['facts'] if f['physical_key'] == key]
        i, meta = metadata[(ent, code)]
        sample_key = ent + '.' + code
        row['frontend_audit_pointer'] = f'/data/frontend_metadata/{i}'
        row['frontend_flags'] = {k: meta.get(k) for k in ['is_visible_on_front', 'is_filterable', 'is_searchable']}
        row['sample_pointer'] = '/data/' + sample_key
        row['sample_rows'] = len(samples.get(sample_key, [])) if sample_key in samples else None
        row['fact_ids'] = ids
        if ids:
            status, reason = 'verified_UI_mapping', 'Same-record independent UI/DB witness; image is resource identity only'
        elif code in navigation:
            status, reason = 'navigation_or_relationship_review', 'Structural/routing source: assess graph or derived UI state, not a separate scalar business-field score'
        elif code in configuration or code.startswith(('meta_', 'custom_', 'use_config_')) or code in {'cost', 'status', 'visibility', 'created_at', 'updated_at', 'page_layout', 'display_mode'}:
            status, reason = 'excluded_scalar_business_scope', 'Configuration/audit/internal policy field; exclusion is a scope decision, not proof of invisibility'
        elif sample_key in samples and not samples[sample_key]:
            status, reason = 'no_stored_value_UI_defaults_unresolved', 'Query found no nonempty stored EAV rows; defaults or derived display still require UI review'
        else:
            status, reason = 'pending_same_record_UI_witness', 'Stored/media/static source exists or is unresolved; require same-record rendered witness before counting'
        row.update(disposition=status, reason=reason)
    result['review_sources'] = [{'file': name, 'sha256': hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}
                                for name in ['db-frontend-audit.20261008.json', 'db-public-samples.20261008.json',
                                             'db-export.v2.json', 'review_candidates_v2.py']]
    result['limitations'] += ['All 92 candidates reviewed, but several dispositions remain unresolved; not complete website gold.',
                             'Snapshot and DB dates differ. Live metadata source is not a full application dataflow proof.',
                             'No network response, relation or UI default is counted solely from EAV flags.']
    target = ROOT / 'db-ui-mapping.v2.json'
    content = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if target.exists() and target.read_text(encoding='utf-8') != content:
        raise RuntimeError('Refuse overwrite; use new version')
    target.write_text(content, encoding='utf-8')
    print(json.dumps(dict(collections.Counter(r['disposition'] for r in result['eav_candidates'])), indent=2))


if __name__ == '__main__':
    main()
