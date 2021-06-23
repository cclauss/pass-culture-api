import flask
import flask_admin
import flask_login
from markupsafe import Markup
import sqlalchemy
import sqlalchemy.orm
import wtforms
import wtforms.validators

from pcapi.admin import base_configuration
from pcapi.admin import templating
import pcapi.core.fraud.models as fraud_models
import pcapi.core.users.api as users_api
import pcapi.core.users.models as users_models
from pcapi.models import db


def beneficiary_fraud_result_formatter(view, context, model, name) -> Markup:
    result_mapping_class = {
        fraud_models.FraudStatus.OK: "badge-success",
        fraud_models.FraudStatus.KO: "badge-danger",
        fraud_models.FraudStatus.SUSPICIOUS: "badge-warning",
    }

    if model.beneficiaryFraudResult:
        instance = model.beneficiaryFraudResult.status
        return Markup(f"""<span class="badge {result_mapping_class[instance]}">{instance.value}</span>""")
    return Markup("""<span class="badge badge-secondary">Inconnu</span>""")


def beneficiary_fraud_review_formatter(view, context, model, name) -> Markup:
    status = templating.yesno(model.beneficiaryFraudReview)
    if model.beneficiaryFraudReview:
        return (
            Markup(
                f"<div><span>{model.beneficiaryFraudReview.author.firstName} {model.beneficiaryFraudReview.author.lastName}</span></div>"
            )
            + status
        )
    return status


def beneficiary_fraud_checks_formatter(view, context, model, name) -> Markup:
    values = []
    for instance in model.beneficiaryFraudChecks:
        values.append(f"<li>{instance.type.value}</li>")

    return Markup(f"""<ul>{"".join(values)}</ul>""")


class FraudReviewForm(wtforms.Form):
    reason = wtforms.TextAreaField(validators=[wtforms.validators.DataRequired()])
    review = wtforms.SelectField(
        choices=[(item.name, item.value) for item in fraud_models.FraudReviewStatus],
        validators=[wtforms.validators.DataRequired()],
    )


class FraudView(base_configuration.BaseAdminView):

    column_list = [
        "id",
        "firstName",
        "lastName",
        "beneficiaryFraudResult",
        "beneficiaryFraudChecks",
        "beneficiaryFraudReview",
    ]
    column_labels = {
        "firstName": "Prénom",
        "lastName": "Nom",
        "beneficiaryFraudResult": "Anti Fraude",
        "beneficiaryFraudChecks": "Vérifications anti fraudes",
        "beneficiaryFraudReview": "Evaluation Manuelle",
    }

    column_searchable_list = ["id", "email", "firstName", "lastName"]
    column_filters = ["postalCode", "email", "beneficiaryFraudResult.status", "beneficiaryFraudChecks.type"]

    can_view_details = True
    details_template = "admin/fraud_details.html"

    @property
    def column_formatters(self):
        formatters = super().column_formatters.copy()
        formatters.update(
            {
                "beneficiaryFraudChecks": beneficiary_fraud_checks_formatter,
                "beneficiaryFraudResult": beneficiary_fraud_result_formatter,
                "beneficiaryFraudReview": beneficiary_fraud_review_formatter,
            }
        )
        return formatters

    def get_query(self):
        return users_models.User.query.filter(
            (users_models.User.beneficiaryFraudChecks.any()) | (users_models.User.beneficiaryFraudResult.has())
        ).options(
            sqlalchemy.orm.joinedload(users_models.User.beneficiaryFraudChecks),
            sqlalchemy.orm.joinedload(users_models.User.beneficiaryFraudResult),
            sqlalchemy.orm.joinedload(users_models.User.beneficiaryFraudReview),
        )

    def get_count_query(self):
        return db.session.query(sqlalchemy.func.count(users_models.User.id)).filter(
            (users_models.User.beneficiaryFraudChecks.any()) | (users_models.User.beneficiaryFraudResult.has())
        )

    @flask_admin.expose("/validate/beneficiary/<user_id>", methods=["POST"])
    def validate_beneficiary(self, user_id):
        form = FraudReviewForm(flask.request.form)
        if not form.validate():
            flask.flash("Erreurs lors de la validation du formulaire", "error")
            return flask.redirect(flask.url_for(".details_view", id=user_id))
        user = (
            users_models.User.query.filter_by(id=user_id)
            .options(sqlalchemy.orm.joinedload(users_models.User.beneficiaryFraudReview))
            .one_or_none()
        )
        if not user:
            return flask.redirect(flask.url_for(".index"))

        if user.beneficiaryFraudReview:
            flask.flash("Une revue manuelle a déjà été réalisée sur le bénéficiaire {user.firstName} {user.lastName}")
            return flask.redirect(flask.url_for(".details_view", id=user_id))

        review = fraud_models.BeneficiaryFraudReview(
            user=user, author=flask_login.current_user, reason=form.data["reason"], review=form.data["review"]
        )
        db.session.add(review)
        db.session.commit()
        users_api.activate_beneficiary(user, "fraud_validation")
        flask.flash(f"Une revue manuelle ajoutée pour le bénéficiaire {user.firstName} {user.lastName}")
        return flask.redirect(flask.url_for(".details_view", id=user_id))
