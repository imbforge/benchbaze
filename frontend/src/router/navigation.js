import axios from "axios";

async function getNavigationTree() {
  try {
    const response = await axios.get(`/api/navigation/`);
    return response.data;
  } catch (error) {
    console.log(error);
  }
}

async function whoami() {
  try {
    const data = await axios.get("/api/auth/user/whoami/");
    return data.data;
  } catch (error) {
    console.log(error);
    return null;
  }
}

function getNavigationModel(models, appLabel, modelName) {
  return models.find(
    (e) =>
      e.app_label === appLabel && e.model_class_name.toLowerCase() === modelName
  );
}

export { getNavigationTree, getNavigationModel, whoami };
