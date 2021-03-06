var menuEvents = new EventEmitter();
var ContextMenuEnum = {
  type: {
    RUN: 1,
    BUNDLE: 2
  },
  command: {
    REMOVE_BUNDLE: 1,
    DETACH_BUNDLE: 2,
    ADD_BUNDLE_TO_HOMEWORKSHEET: 3,
    KILL_BUNDLE: 4
  }
};
var ContextMenuMixin = {
  openContextMenu: function(type, callback){
    menuEvents.emit('open', {
      type: type,
      callback: callback,
    });
  },
  closeContextMenu: function(){
    menuEvents.emit('close');
  }
};

var mouse = {x: 0, y: 0};
var updateMouse = function(e){
  mouse.x = e.pageX;
  mouse.y = e.pageY;
};

var ContextMenu = React.createClass({
  getInitialState: function(){
    var bundleMap = {
      'Remove bundle permanently': [ContextMenuEnum.command.REMOVE_BUNDLE, ['rm']],
      'Detach from this worksheet': [ContextMenuEnum.command.DETACH_BUNDLE, ['detach']],
      'Add to my home worksheet': [ContextMenuEnum.command.ADD_BUNDLE_TO_HOMEWORKSHEET, ['add', 'bundle']]
    };
    var runBundleMap = _.extend({}, bundleMap, {'Kill this run bundle': [ContextMenuEnum.command.KILL_BUNDLE, ['kill']]});
    labelMap = {}
    labelMap[ContextMenuEnum.type.RUN] = runBundleMap;
    labelMap[ContextMenuEnum.type.BUNDLE] = bundleMap;

    return {
      type: null,
      callback: null,
      labelMap: labelMap
    };
  },

  componentDidMount: function(){
    menuEvents.on('open', this.handleOpenEvent);
    menuEvents.on('close', this.closeMenu);
    addEventListener('mousemove', updateMouse);
    document.onclick = ContextMenuMixin.closeContextMenu;
  },

  handleOpenEvent: function(payload){
    this.setState(_.extend(payload, mouse));
    $('.ws-container').css({'overflow': 'hidden'});
  },

  closeMenu: function(){
    this.replaceState(this.getInitialState());
    $('.ws-container').css({'overflow': 'auto'});
  },

  render: function(){
    if (!this.state.type) {
      return null;
    }
    // estimate of the height and weight of the context menu
    var height = 32 * Object.keys(this.state.labelMap[this.state.type]).length;
    var width = 250;
    var style = {
      left: Math.min(this.state.x, window.innerWidth - width),
      // avoid overflow below the window limit (30 is the height of the bottom bar)
      top: Math.min(this.state.y, window.innerHeight - height - 30),
      position: 'fixed'
    };

    return (
      <div className="context-menu" style={style}>
        {Object.keys(this.state.labelMap[this.state.type]).map(function(display, i){
            return <div className="context-menu-item" key={i} onClick={this.makeClickHandler(this.state.labelMap[this.state.type][display])}>
                    {display}
                   </div>
          }, this)}
      </div>
    );
  },

  makeClickHandler: function(option) {
    return function(){
      if (this.state.callback) {
        this.state.callback(option);
        this.replaceState(this.getInitialState());
      }
    }.bind(this);
  }
});
