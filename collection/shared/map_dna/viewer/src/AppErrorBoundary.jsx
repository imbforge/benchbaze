import React from "react";

class ViewerErrorBoundary extends React.Component {
 // Component designed to catch errors in its child components and 
 // display a fallback UI instead of crashing the entire app
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  // This lifecycle method is called when a child component throws an error
  static getDerivedStateFromError(error) {
    return { error };
  }

  // This lifecycle method is called after the component updates, allowing to reset 
  // the error state when the resetKey prop changes
  componentDidUpdate(prevProps) {
    if (
      prevProps.resetKey !== this.props.resetKey &&
      this.state.error !== null
    ) {
      this.setState({ error: null });
    }
  }

  render() {
    if (this.state.error) {
      return this.props.renderError(this.state.error);
    }

    return this.props.children;
  }
}

export default ViewerErrorBoundary;
