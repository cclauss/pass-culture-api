""" mediations """
from flask import current_app as app, jsonify, request
from flask_login import current_user, login_required

from models.api_errors import ApiErrors
from models.mediation import Mediation
from models.pc_object import PcObject
from models.user_offerer import RightsType
from utils.human_ids import dehumanize
from utils.rest import ensure_current_user_has_rights, load_or_404, expect_json_data
from utils.thumb import has_thumb, read_thumb


@app.route('/mediations', methods=['POST'])
@login_required
def create_mediation():

    if not has_thumb():
        api_errors = ApiErrors()
        api_errors.addError('thumb', "Vous devez fournir une image d'accroche")
        return jsonify(api_errors.errors), 400

    offerer_id = dehumanize(request.form['offererId'])
    ensure_current_user_has_rights(RightsType.editor, offerer_id)

    new_mediation = Mediation()
    new_mediation.author = current_user
    new_mediation.offerId = dehumanize(request.form['offerId'])
    new_mediation.credit = request.form.get('credit')
    new_mediation.offererId = offerer_id
    PcObject.check_and_save(new_mediation)

    crop = [float(request.form['croppingRect[x]']),
            float(request.form['croppingRect[y]']),
            float(request.form['croppingRect[height]'])]

    new_mediation.save_thumb(read_thumb(), 0, crop=crop)

    return jsonify(new_mediation), 201


@app.route('/mediations/<mediation_id>', methods=['GET'])
@login_required
def get_mediation(mediation_id):
    mediation = load_or_404(Mediation, mediation_id)
    return jsonify(mediation._asdict())


@app.route('/mediations/<mediation_id>', methods=['PATCH'])
@login_required
@expect_json_data
def update_mediation(mediation_id):
    mediation = load_or_404(Mediation, mediation_id)
    ensure_current_user_has_rights(RightsType.editor, mediation.offer.venue.managingOffererId)
    mediation = Mediation.query.filter_by(id=dehumanize(mediation_id)).first()
    mediation.populateFromDict(request.json)
    PcObject.check_and_save(mediation)
    return jsonify(mediation._asdict()), 200
