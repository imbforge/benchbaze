import axios from "axios";

const redirectToLogin = () => {
  try {
    window.location.href = `${djangoSettings.login_url ? djangoSettings.login_url : "/login/"}?next=${import.meta.env.BASE_URL}`;
  } catch {
    window.location.href = `/login/?next=${import.meta.env.BASE_URL}`;
  }
};

// Get some general settings from Django
const getDjangoSettings = async () => {
  try {
    const response = await axios.get(`/api/settings/`);
    return response.data;
  } catch (error) {
    console.error(error);
    redirectToLogin();
  }
};

const djangoSettings = await getDjangoSettings();
if (djangoSettings.lab_name) {
  window.document.title = `BenchBaze @ ${djangoSettings.lab_name}`;
}

// Get app/model tree
async function getNavigationTree() {
  try {
    const response = await axios.get(`/api/navigation/`);
    // Generate the path to a model
    response.data.forEach((model) => {
      model.path = `/${model.app_label}/${model.model_class_name.toLowerCase()}`;
    });
    return response.data;
  } catch (error) {
    if (error.response.status == 403) {
      redirectToLogin();
    } else {
      console.log(error.response.data.detail);
    }
  }
}

// Get the authenticated user
async function getLoggedUser() {
  try {
    const data = await axios.get("/api/common/user/logged/");
    return data.data;
  } catch (error) {
    if (error.response.status == 403) {
      redirectToLogin();
    } else {
      console.log(error.response.data.detail);
      return null;
    }
  }
}

// Get a model from a list of models
function getNavigationModel(models, appLabel, modelName) {
  let model = models.find(
    (e) =>
      e.app_label === appLabel && e.model_class_name.toLowerCase() === modelName
  );

  // If no model can be found return an empty model
  if (model === undefined) {
    model = {
      id: null,
      app_label: appLabel,
      app_verbose_name: null,
      model_class_name: modelName,
      model_verbose_name: null,
      model_verbose_plural: null,
      permissions: {
        add: false,
        change: false,
        view: false
      }
    };
  }

  return model;
}

export { getNavigationTree, getNavigationModel, getLoggedUser, djangoSettings };
